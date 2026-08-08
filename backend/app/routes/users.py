"""Gestion des utilisateurs et réinitialisation mot de passe."""
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, validate
from marshmallow import fields as mfields

from app.auth.jwt_handler import get_current_user, hash_password
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import ReinitialisationMdp, Utilisateur
from app.schemas.auth import UserSchema
from app.utils.audit_logger import log_audit

blp = Blueprint("users", __name__, url_prefix="/users", description="Utilisateurs")


class CreateUserSchema(Schema):
    nom = mfields.String(required=True)
    prenom = mfields.String(required=True)
    email = mfields.Email(required=True)
    telephone = mfields.String(allow_none=True)
    role = mfields.String(
        required=True,
        validate=validate.OneOf(
            ["administrateur", "directeur", "secretariat", "enseignant", "agent_comptable", "parent"]
        ),
    )
    password = mfields.String(required=True, validate=validate.Length(min=8))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@blp.route("")
class UsersList(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def get(self):
        db = get_db()
        users = db.query(Utilisateur).order_by(Utilisateur.nom, Utilisateur.prenom).all()
        return jsonify([UserSchema().dump(u) for u in users])

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(CreateUserSchema)
    def post(self, data):
        db = get_db()
        if db.query(Utilisateur).filter(Utilisateur.email == data["email"]).first():
            return jsonify({"message": "Email déjà utilisé"}), 409
        user = Utilisateur(
            id=uuid.uuid4(),
            nom=data["nom"],
            prenom=data["prenom"],
            email=data["email"],
            telephone=data.get("telephone"),
            role=data["role"],
            mot_de_passe_hash=hash_password(data["password"]),
            actif=True,
            doit_changer_mdp=True,
        )
        db.add(user)
        db.commit()
        log_audit("CREATION_UTILISATEUR", get_current_user().id, "utilisateur", user.id)
        return UserSchema().dump(user), 201


@blp.route("/<uuid:id_user>")
class UserDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def patch(self, id_user):
        db = get_db()
        user = db.query(Utilisateur).filter(Utilisateur.id == id_user).first()
        if not user:
            return jsonify({"message": "Utilisateur introuvable"}), 404
        data = request.json or {}
        if "actif" in data:
            user.actif = bool(data["actif"])
        if "role" in data and data["role"] in (
            "administrateur", "directeur", "secretariat", "enseignant", "agent_comptable", "parent"
        ):
            user.role = data["role"]
        for field in ("nom", "prenom", "email", "telephone"):
            if data.get(field):
                setattr(user, field, data[field])
        db.commit()
        return UserSchema().dump(user)


@blp.route("/<uuid:id_user>/reset-password")
class AdminResetPassword(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def post(self, id_user):
        db = get_db()
        user = db.query(Utilisateur).filter(Utilisateur.id == id_user).first()
        if not user:
            return jsonify({"message": "Utilisateur introuvable"}), 404
        temp = secrets.token_urlsafe(12)
        user.mot_de_passe_hash = hash_password(temp)
        user.doit_changer_mdp = True
        user.tentatives_echouees = 0
        user.verrouille_jusqu_a = None
        db.commit()
        log_audit("REINITIALISATION_MDP", get_current_user().id, "utilisateur", user.id)
        return jsonify({"message": "Mot de passe réinitialisé", "mot_de_passe_temporaire": temp})


@blp.route("/forgot-password")
class ForgotPassword(MethodView):
    def post(self):
        email = (request.json or {}).get("email", "").strip().lower()
        if not email:
            return jsonify({"message": "Email requis"}), 400
        db = get_db()
        user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        if not user:
            return jsonify({"message": "Si le compte existe, un lien a été envoyé"}), 200
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
        payload = {"message": "Si le compte existe, un lien a été envoyé"}
        from flask import current_app

        if current_app.config.get("DEBUG"):
            payload["reset_token"] = token
        return jsonify(payload)


@blp.route("/reset-password")
class ResetPasswordToken(MethodView):
    def post(self):
        data = request.json or {}
        token = data.get("token")
        new_password = data.get("nouveau_mot_de_passe")
        if not token or not new_password or len(new_password) < 8:
            return jsonify({"message": "Token et mot de passe (8+ car.) requis"}), 400
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
