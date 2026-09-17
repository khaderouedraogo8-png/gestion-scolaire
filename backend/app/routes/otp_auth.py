"""OTP auth — demande et vérification (login parent)."""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from flask import jsonify
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


def _resolve_school_and_user(db, destinataire: str, school_code: str | None):
    """Retrouve un parent/utilisateur et son école pour l'OTP login_parent."""
    from app.models import School

    dest = destinataire.strip().lower()
    user = None
    school = None

    if school_code:
        school = db.query(School).filter(School.code == school_code.strip().upper()).first()
        if not school:
            return None, None

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

    return school, user


@blp.route("/otp/request")
class OtpRequest(MethodView):
    @blp.arguments(OtpRequestSchema)
    @limiter.limit("5 per minute")
    def post(self, data):
        db = get_db()
        purpose = data.get("purpose") or PURPOSE_LOGIN_PARENT
        if purpose != PURPOSE_LOGIN_PARENT:
            return jsonify({"message": "Purpose non supporté"}), 400

        school, user = _resolve_school_and_user(
            db, data["destinataire"], data.get("school_code")
        )
        if not school:
            # Réponse neutre anti-énumération
            return jsonify({
                "message": "Si le destinataire est connu, un code a été envoyé.",
                "expires_in_seconds": OTP_TTL_MINUTES * 60,
            }), 200

        code = _generate_code()
        challenge = OtpChallenge(
            id=uuid.uuid4(),
            school_id=school.id,
            canal=data.get("canal") or "sms",
            destinataire=data["destinataire"].strip(),
            code_hash=_hash_code(code),
            purpose=purpose,
            attempts=0,
            max_attempts=5,
            expires_at=datetime.now(UTC) + timedelta(minutes=OTP_TTL_MINUTES),
            id_utilisateur=user.id if user else None,
        )
        db.add(challenge)
        db.commit()

        # En sandbox / test : exposer le code uniquement si DEBUG
        from flask import current_app

        payload = {
            "message": "Code OTP envoyé.",
            "challenge_id": str(challenge.id),
            "expires_in_seconds": OTP_TTL_MINUTES * 60,
            "canal": challenge.canal,
        }
        if current_app.config.get("TESTING") or current_app.debug:
            payload["debug_code"] = code

        log_audit(
            "OTP_REQUEST",
            user.id if user else None,
            "otp_challenge",
            challenge.id,
            details={"canal": challenge.canal, "purpose": purpose},
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

        if challenge.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
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
