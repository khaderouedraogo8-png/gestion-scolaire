"""OTP auth — demande et vérification (login parent) + canal SMS réel."""
from __future__ import annotations

import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from flask import current_app, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint
from marshmallow import Schema, fields, validate
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth.jwt_handler import create_tokens_for_user, set_refresh_cookie
from app.extensions import get_db, limiter
from app.models import OtpChallenge, ParentTuteur, Utilisateur
from app.schemas.auth import UserSchema
from app.utils.audit_logger import log_audit

blp = Blueprint("otp_auth", __name__, description="Authentification OTP")

OTP_TTL_MINUTES = 10
PURPOSE_LOGIN_PARENT = "login_parent"
# Rate-limit applicatif par destinataire (en plus du limiter Flask)
OTP_MAX_PER_DEST_WINDOW = 5
OTP_DEST_WINDOW_MINUTES = 15


class OtpRequestSchema(Schema):
    destinataire = fields.String(required=True)
    canal = fields.String(load_default="sms", validate=validate.OneOf(["sms", "email", "whatsapp"]))
    purpose = fields.String(load_default=PURPOSE_LOGIN_PARENT)
    school_code = fields.String(allow_none=True)


class OtpVerifySchema(Schema):
    destinataire = fields.String(required=True)
    code = fields.String(required=True)
    purpose = fields.String(load_default=PURPOSE_LOGIN_PARENT)
    challenge_id = fields.UUID(allow_none=True)


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_code(code: str) -> str:
    return generate_password_hash(code, method="pbkdf2:sha256")


def _check_code(code_hash: str, code: str) -> bool:
    return check_password_hash(code_hash, code)


def _looks_like_phone(value: str) -> bool:
    digits = re.sub(r"\D+", "", value or "")
    return 8 <= len(digits) <= 15 and "@" not in (value or "")


def _sms_api_configured() -> bool:
    return bool((current_app.config.get("SMS_API_URL") or "").strip())


def _resolve_school_and_user(db, destinataire: str, school_code: str | None):
    """Retrouve un parent/utilisateur et son école pour l'OTP login_parent."""
    from app.models import School

    user = None
    school = None
    parent = None

    if school_code:
        school = db.query(School).filter(School.code == school_code.strip().upper()).first()
        if not school:
            return None, None, None

    q_user = db.query(Utilisateur).filter(
        Utilisateur.email == destinataire.strip(),
        Utilisateur.role == "parent",
        Utilisateur.actif.is_(True),
    )
    if school:
        q_user = q_user.filter(Utilisateur.school_id == school.id)
    user = q_user.first()

    if not user:
        q_parent = db.query(ParentTuteur).filter(
            (ParentTuteur.email == destinataire.strip()) | (ParentTuteur.telephone == destinataire.strip())
        )
        if school:
            q_parent = q_parent.filter(ParentTuteur.school_id == school.id)
        parent = q_parent.first()
        if parent and parent.id_utilisateur:
            user = db.query(Utilisateur).filter(Utilisateur.id == parent.id_utilisateur).first()
            if not school:
                school = db.query(School).filter(School.id == parent.school_id).first()
        elif parent:
            if not school:
                school = db.query(School).filter(School.id == parent.school_id).first()

    if user and not school:
        school = db.query(School).filter(School.id == user.school_id).first()

    if user and not parent:
        parent = (
            db.query(ParentTuteur)
            .filter(ParentTuteur.id_utilisateur == user.id)
            .first()
        )

    return school, user, parent


def _rate_limit_destinataire(db, destinataire: str, purpose: str, school_id) -> bool:
    """True si trop de challenges récents pour ce destinataire."""
    since = datetime.now(UTC) - timedelta(minutes=OTP_DEST_WINDOW_MINUTES)
    q = db.query(OtpChallenge).filter(
        OtpChallenge.destinataire == destinataire.strip(),
        OtpChallenge.purpose == purpose,
        OtpChallenge.created_at >= since,
    )
    if school_id:
        q = q.filter(OtpChallenge.school_id == school_id)
    return q.count() >= OTP_MAX_PER_DEST_WINDOW


def _dispatch_otp(code: str, canal: str, destinataire: str, parent: ParentTuteur | None) -> list[str]:
    """Envoie le code sur le canal demandé + SMS si SMS_API configuré (login_parent)."""
    from app.services.envoi_notification import get_provider

    sent: list[str] = []
    body = f"Votre code de connexion parent : {code} (valide {OTP_TTL_MINUTES} min)."

    # Canal demandé
    try:
        dest = destinataire
        if canal == "email":
            dest = destinataire if "@" in destinataire else (parent.email if parent else destinataire)
        elif canal in ("sms", "whatsapp"):
            dest = destinataire if _looks_like_phone(destinataire) else (
                parent.telephone if parent and parent.telephone else destinataire
            )
        ok = get_provider(canal).envoyer(dest, body, sujet="Code OTP — Espace parent")
        if ok:
            sent.append(canal)
    except Exception:
        current_app.logger.exception("OTP envoi canal=%s échoué", canal)

    # Profondeur SMS : si API SMS configurée, tenter aussi le SMS (login_parent)
    if _sms_api_configured():
        phone = None
        if _looks_like_phone(destinataire):
            phone = destinataire.strip()
        elif parent and parent.telephone:
            phone = parent.telephone.strip()
        if phone and "sms" not in sent:
            try:
                ok = get_provider("sms").envoyer(phone, body, sujet="Code OTP")
                if ok:
                    sent.append("sms")
            except Exception:
                current_app.logger.exception("OTP SMS secondaire échoué")

    return sent


@blp.route("/otp/request")
class OtpRequest(MethodView):
    @blp.arguments(OtpRequestSchema)
    @limiter.limit("5 per minute")
    def post(self, data):
        db = get_db()
        purpose = data.get("purpose") or PURPOSE_LOGIN_PARENT
        if purpose != PURPOSE_LOGIN_PARENT:
            return jsonify({"message": "Purpose non supporté"}), 400

        destinataire = data["destinataire"].strip()
        school, user, parent = _resolve_school_and_user(
            db, destinataire, data.get("school_code")
        )
        if not school:
            # Réponse neutre anti-énumération
            return jsonify({
                "message": "Si le destinataire est connu, un code a été envoyé.",
                "expires_in_seconds": OTP_TTL_MINUTES * 60,
            }), 200

        if _rate_limit_destinataire(db, destinataire, purpose, school.id):
            return jsonify({
                "message": "Trop de demandes. Réessayez plus tard.",
            }), 429

        canal = data.get("canal") or "sms"
        # Si SMS_API configuré et destinataire téléphone → forcer canal sms stocké
        if _sms_api_configured() and _looks_like_phone(destinataire):
            canal = "sms"

        code = _generate_code()
        challenge = OtpChallenge(
            id=uuid.uuid4(),
            school_id=school.id,
            canal=canal,
            destinataire=destinataire,
            code_hash=_hash_code(code),
            purpose=purpose,
            attempts=0,
            max_attempts=5,
            expires_at=datetime.now(UTC) + timedelta(minutes=OTP_TTL_MINUTES),
            id_utilisateur=user.id if user else None,
        )
        db.add(challenge)
        db.commit()

        channels_sent = _dispatch_otp(code, canal, destinataire, parent)

        payload = {
            "message": "Code OTP envoyé.",
            "challenge_id": str(challenge.id),
            "expires_in_seconds": OTP_TTL_MINUTES * 60,
            "canal": challenge.canal,
            "channels_attempted": channels_sent,
        }
        if current_app.config.get("TESTING") or current_app.debug:
            payload["debug_code"] = code

        log_audit(
            "OTP_REQUEST",
            user.id if user else None,
            "otp_challenge",
            challenge.id,
            details={
                "canal": challenge.canal,
                "purpose": purpose,
                "channels_attempted": channels_sent,
                "sms_api": _sms_api_configured(),
            },
        )
        return jsonify(payload), 200


@blp.route("/otp/verify")
class OtpVerify(MethodView):
    @blp.arguments(OtpVerifySchema)
    @limiter.limit("10 per minute")
    def post(self, data):
        db = get_db()
        purpose = data.get("purpose") or PURPOSE_LOGIN_PARENT
        q = db.query(OtpChallenge).filter(
            OtpChallenge.destinataire == data["destinataire"].strip(),
            OtpChallenge.purpose == purpose,
            OtpChallenge.consumed_at.is_(None),
        )
        if data.get("challenge_id"):
            q = q.filter(OtpChallenge.id == data["challenge_id"])
        challenge = q.order_by(OtpChallenge.created_at.desc()).first()
        if not challenge:
            return jsonify({"message": "Challenge introuvable ou expiré"}), 404

        expires = challenge.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires < datetime.now(UTC):
            return jsonify({"message": "Code expiré"}), 410

        if challenge.attempts >= challenge.max_attempts:
            return jsonify({"message": "Trop de tentatives"}), 429

        challenge.attempts += 1
        if not _check_code(challenge.code_hash, data["code"].strip()):
            db.commit()
            return jsonify({"message": "Code invalide"}), 401

        challenge.consumed_at = datetime.now(UTC)
        db.commit()

        user = None
        if challenge.id_utilisateur:
            user = db.query(Utilisateur).filter(Utilisateur.id == challenge.id_utilisateur).first()

        log_audit(
            "OTP_VERIFY_OK",
            user.id if user else None,
            "otp_challenge",
            challenge.id,
            details={"purpose": purpose},
        )
        if user and user.actif:
            access_token, raw_refresh, _ = create_tokens_for_user(user)
            response = jsonify({
                "verified": True,
                "access_token": access_token,
                "user": UserSchema().dump(user),
                "user_id": str(user.id),
            })
            return set_refresh_cookie(response, raw_refresh), 200

        return jsonify({
            "verified": True,
            "user_id": None,
            "message": "Code valide — aucun compte parent lié",
        }), 200
