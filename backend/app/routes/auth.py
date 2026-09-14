"""Routes authentification : login, refresh, logout, changement MDP."""
import hashlib
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from flask import jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.jwt_handler import (
    clear_refresh_cookie,
    create_tokens_for_user,
    get_current_user,
    get_refresh_from_cookie,
    hash_password,
    revoke_refresh_token,
    rotate_refresh_token,
    set_refresh_cookie,
    verify_password,
)
from app.extensions import get_db, limiter
from app.models import ReinitialisationMdp, Utilisateur
from app.schemas.auth import (
    ChangePasswordSchema,
    ForgotPasswordSchema,
    LoginSchema,
    ResetPasswordSchema,
    UserSchema,
)
from app.utils.audit_logger import log_audit

blp = Blueprint("auth", __name__, url_prefix="/auth", description="Authentification")


@blp.route("/login")
class Login(MethodView):
    @blp.arguments(LoginSchema)
    @limiter.limit("5 per minute")
    def post(self, credentials):
        db = get_db()
        user = db.query(Utilisateur).filter(Utilisateur.email == credentials["email"]).first()

        if not user:
            log_audit("ECHEC_CONNEXION", details={"email": credentials["email"], "raison": "email_inconnu"})
            return jsonify({"message": "Identifiants invalides"}), 401

        # Vérifier verrouillage compte
        if user.verrouille_jusqu_a and user.verrouille_jusqu_a > datetime.now(UTC):
            return jsonify({"message": "Compte verrouillé — réessayez plus tard"}), 423

        if not verify_password(user.mot_de_passe_hash, credentials["password"]):
            user.tentatives_echouees = (user.tentatives_echouees or 0) + 1
            if user.tentatives_echouees >= 5:
                user.verrouille_jusqu_a = datetime.now(UTC) + timedelta(minutes=30)
            db.commit()
            log_audit("ECHEC_CONNEXION", user.id, details={"tentatives": user.tentatives_echouees})
            return jsonify({"message": "Identifiants invalides"}), 401

        if not user.actif:
            return jsonify({"message": "Compte désactivé"}), 403

        user.tentatives_echouees = 0
        user.verrouille_jusqu_a = None
        user.derniere_connexion = datetime.now(UTC)
        db.commit()

        access_token, raw_refresh, _ = create_tokens_for_user(user)
        log_audit("CONNEXION", user.id)

        response = jsonify({
            "access_token": access_token,
            "user": UserSchema().dump(user),
            "doit_changer_mdp": user.doit_changer_mdp,
        })
        return set_refresh_cookie(response, raw_refresh), 200


@blp.route("/refresh")
class Refresh(MethodView):
    def post(self):
        raw_refresh = get_refresh_from_cookie()
        if not raw_refresh:
            return jsonify({"message": "Refresh token manquant"}), 401

        result = rotate_refresh_token(raw_refresh)
        if not result:
            response = jsonify({"message": "Refresh token invalide ou expiré"})
            return clear_refresh_cookie(response), 401

        access_token, new_raw_refresh = result
        response = jsonify({"access_token": access_token})
        return set_refresh_cookie(response, new_raw_refresh), 200


@blp.route("/logout")
class Logout(MethodView):
    @jwt_required()
    def post(self):
        raw_refresh = get_refresh_from_cookie()
        if raw_refresh:
            revoke_refresh_token(raw_refresh)
        user = get_current_user()
        if user:
            log_audit("DECONNEXION", user.id)
        response = jsonify({"message": "Déconnecté"})
        return clear_refresh_cookie(response), 200


@blp.route("/me")
class Me(MethodView):
    @jwt_required()
    @blp.response(200, UserSchema)
    def get(self):
        user = get_current_user()
        return user


@blp.route("/change-password")
class ChangePassword(MethodView):
    @jwt_required()
    @blp.arguments(ChangePasswordSchema)
    def post(self, data):
        user = get_current_user()
        if not verify_password(user.mot_de_passe_hash, data["ancien_mot_de_passe"]):
            return jsonify({"message": "Ancien mot de passe incorrect"}), 400

        db = get_db()
        user.mot_de_passe_hash = hash_password(data["nouveau_mot_de_passe"])
        user.doit_changer_mdp = False
        db.commit()
        log_audit("CHANGEMENT_MDP", user.id)
        return jsonify({"message": "Mot de passe modifié"}), 200


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

@blp.route("/forgot-password")
class ForgotPassword(MethodView):
    @blp.arguments(ForgotPasswordSchema)
    def post(self, data):
        """Demande de reset MDP.

        Règles P0 :
        - DEBUG seul ne suffit JAMAIS à exposer le token.
        - EXPOSE_RESET_TOKEN=1 uniquement hors production (et tests).
        - Sans SMTP configuré et sans expose → 503, pas de faux envoi.
        """
        from flask import current_app

        email = data["email"].strip().lower()

        is_prod = (
            os.getenv("FLASK_ENV", "").lower() == "production"
            or current_app.config.get("ENV") == "production"
        )
        expose_flag = os.getenv("EXPOSE_RESET_TOKEN", "").strip().lower() in ("1", "true", "yes")
        # Impossible d'exposer le token en production, même avec EXPOSE_RESET_TOKEN=1
        expose = (expose_flag and not is_prod) or current_app.config.get("TESTING")

        smtp_host = (current_app.config.get("SMTP_HOST") or os.getenv("SMTP_HOST") or "").strip()
        smtp_enabled = os.getenv("SMTP_ENABLED", "").strip().lower() in ("1", "true", "yes")
        # localhost seul (défaut config) ≠ SMTP production ; exiger SMTP_ENABLED ou un hôte réel
        smtp_configured = smtp_enabled or (
            bool(smtp_host)
            and smtp_host.lower() not in ("", "none", "disabled", "localhost", "127.0.0.1")
        )

        if not expose and not smtp_configured:
            current_app.logger.error(
                "forgot-password: SMTP non configuré — service indisponible (aucun token exposé)"
            )
            return jsonify({
                "message": "Service de récupération de mot de passe temporairement indisponible."
            }), 503

        db = get_db()
        user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        # Réponse générique anti-énumération
        generic = {"message": "Si le compte existe, un lien a été envoyé"}
        if not user:
            return jsonify(generic), 200

        token = secrets.token_urlsafe(32)
        db.add(
            ReinitialisationMdp(
                id=uuid.uuid4(),
                id_utilisateur=user.id,
                token_hash=_hash_token(token),
                expire_at=datetime.now(UTC) + timedelta(hours=24),
            )
        )
        db.commit()

        if expose:
            # Dev/tests uniquement — jamais en production
            return jsonify({**generic, "reset_token": token}), 200

        # Envoi email réel (sans renvoyer le token)
        try:
            from app.services.envoi_notification import SMTPProvider

            reset_url = f"{os.getenv('APP_PUBLIC_URL', '').rstrip('/')}/reset-password?token={token}"
            body = (
                "Bonjour,\n\n"
                "Une demande de réinitialisation de mot de passe a été effectuée.\n"
                f"Lien (valide 24h) : {reset_url}\n\n"
                "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n"
            )
            ok = SMTPProvider().envoyer(user.email, body, "Réinitialisation du mot de passe")
            if not ok:
                current_app.logger.error("forgot-password: échec envoi SMTP pour user_id=%s", user.id)
                return jsonify({
                    "message": "Service de récupération de mot de passe temporairement indisponible."
                }), 503
        except Exception:
            current_app.logger.exception("forgot-password: erreur technique (token non exposé)")
            return jsonify({
                "message": "Service de récupération de mot de passe temporairement indisponible."
            }), 503

        return jsonify(generic), 200



@blp.route("/reset-password")
class ResetPasswordToken(MethodView):
    @blp.arguments(ResetPasswordSchema)
    def post(self, data):
        token = data["token"]
        new_password = data["nouveau_mot_de_passe"]
        db = get_db()
        row = (
            db.query(ReinitialisationMdp)
            .filter(
                ReinitialisationMdp.token_hash == _hash_token(token),
                ReinitialisationMdp.utilise.is_(False),
            )
            .first()
        )
        if not row or row.expire_at < datetime.now(UTC):
            return jsonify({"message": "Lien invalide ou expiré"}), 400
        user = db.query(Utilisateur).filter(Utilisateur.id == row.id_utilisateur).first()
        user.mot_de_passe_hash = hash_password(new_password)
        user.doit_changer_mdp = False
        row.utilise = True
        db.commit()
        return jsonify({"message": "Mot de passe mis à jour"})

