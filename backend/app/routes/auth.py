"""Routes authentification : login, refresh, logout, changement MDP."""
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
from app.models import Utilisateur
from app.schemas.auth import ChangePasswordSchema, LoginSchema, UserSchema
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
