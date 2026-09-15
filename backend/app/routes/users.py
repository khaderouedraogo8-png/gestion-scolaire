"""Gestion des utilisateurs et réinitialisation mot de passe."""
import secrets
import uuid

from flask import jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, validate
from marshmallow import fields as mfields

from app.auth.jwt_handler import get_current_user, hash_password
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import Utilisateur
from app.models.utilisateur import SCHOOL_ROLES
from app.schemas.auth import (
    UpdateUserSchema,
    UserSchema,
)
from app.services.platform_schools import ensure_not_last_school_admin
from app.services.tenant import apply_tenant_school, get_or_404_tenant, reject_client_school_id, tenant_query
from app.utils.audit_logger import log_audit
from app.utils.pagination import paginate_query, pagination_payload, parse_pagination

blp = Blueprint("users", __name__, description="Utilisateurs")


class CreateUserSchema(Schema):
    class Meta:
        unknown = "include"

    nom = mfields.String(required=True)
    prenom = mfields.String(required=True)
    email = mfields.Email(required=True)
    telephone = mfields.String(allow_none=True)
    role = mfields.String(
        required=True,
        validate=validate.OneOf(list(SCHOOL_ROLES)),
    )
    password = mfields.String(required=True, validate=validate.Length(min=8))


@blp.route("")
class UsersList(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def get(self):
        get_db()
        page, per_page = parse_pagination(default_per_page=50)
        items, total, pages = paginate_query(
            tenant_query(Utilisateur).order_by(Utilisateur.nom, Utilisateur.prenom),
            page,
            per_page,
        )
        return jsonify(
            pagination_payload(
                [UserSchema().dump(u) for u in items],
                page=page,
                per_page=per_page,
                total=total,
                pages=pages,
            )
        )

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(CreateUserSchema)
    def post(self, data):
        reject_client_school_id(data)
        if data["role"] not in SCHOOL_ROLES:
            return jsonify({"message": "Rôle invalide"}), 400
        db = get_db()
        if db.query(Utilisateur).filter(Utilisateur.email == data["email"]).first():
            return jsonify({"message": "Email déjà utilisé"}), 409
        user = apply_tenant_school(
            Utilisateur(
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
        )
        db.add(user)
        db.commit()
        log_audit("CREATION_UTILISATEUR", get_current_user().id, "utilisateur", user.id)
        return UserSchema().dump(user), 201


@blp.route("/roles")
class UsersRoles(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def get(self):
        """Liste des rôles école assignables (jamais super_admin)."""
        return jsonify({"roles": list(SCHOOL_ROLES)})


@blp.route("/<uuid:id_user>")
class UserDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(UpdateUserSchema)
    def patch(self, data, id_user):
        reject_client_school_id(data)
        db = get_db()
        user = get_or_404_tenant(Utilisateur, id_user)
        actor = get_current_user()

        if "role" in data:
            if data["role"] not in SCHOOL_ROLES:
                return jsonify({"message": "Rôle invalide ou promotion SUPER_ADMIN interdite"}), 403
            if user.role == "administrateur" and data["role"] != "administrateur":
                ensure_not_last_school_admin(user)
            old_role = user.role
            user.role = data["role"]
            if old_role != data["role"]:
                log_audit(
                    "ROLE_CHANGED",
                    actor.id,
                    "utilisateur",
                    user.id,
                    details={"old_role": old_role, "new_role": data["role"]},
                )

        if "actif" in data:
            new_actif = bool(data["actif"])
            if user.actif and not new_actif:
                ensure_not_last_school_admin(user)
            user.actif = new_actif
            log_audit(
                "USER_ACTIVATED" if new_actif else "USER_DEACTIVATED",
                actor.id,
                "utilisateur",
                user.id,
            )

        for field in ("nom", "prenom", "email", "telephone"):
            if field in data and data[field] is not None:
                setattr(user, field, data[field])
        db.commit()
        return UserSchema().dump(user)


@blp.route("/<uuid:id_user>/reset-password")
class AdminResetPassword(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def post(self, id_user):
        db = get_db()
        user = get_or_404_tenant(Utilisateur, id_user)
        temp = secrets.token_urlsafe(12)
        user.mot_de_passe_hash = hash_password(temp)
        user.doit_changer_mdp = True
        user.tentatives_echouees = 0
        user.verrouille_jusqu_a = None
        db.commit()
        log_audit("REINITIALISATION_MDP", get_current_user().id, "utilisateur", user.id)
        return jsonify({"message": "Mot de passe réinitialisé", "mot_de_passe_temporaire": temp})


@blp.route("/<uuid:id_user>/toggle-actif")
class ToggleActif(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def post(self, id_user):
        db = get_db()
        user = get_or_404_tenant(Utilisateur, id_user)
        actor = get_current_user()
        if user.actif:
            ensure_not_last_school_admin(user)
            user.actif = False
            action = "USER_DEACTIVATED"
        else:
            user.actif = True
            action = "USER_ACTIVATED"
        db.commit()
        log_audit(action, actor.id, "utilisateur", user.id)
        return UserSchema().dump(user)
