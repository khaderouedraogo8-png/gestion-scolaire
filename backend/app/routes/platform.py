"""Routes plateforme SUPER_ADMIN — écoles, onboarding, school context."""
from __future__ import annotations

import uuid

from flask import jsonify
from flask.views import MethodView
from flask_jwt_extended import get_jwt, jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields, validate
from sqlalchemy import func

from app.auth.jwt_handler import build_access_token_for_user, get_current_user
from app.auth.permissions import require_super_admin
from app.extensions import get_db
from app.models import Eleve, School, Utilisateur
from app.schemas.auth import UserSchema
from app.services.platform_schools import create_school_admin, onboard_school
from app.services.tenant import reject_client_school_id
from app.utils.audit_logger import log_audit
from app.utils.pagination import paginate_query, pagination_payload, parse_pagination

blp = Blueprint(
    "platform",
    __name__,
    description="Console plateforme SUPER_ADMIN",
)


class PlatformSchoolSchema(Schema):
    id = fields.UUID(dump_only=True)
    name = fields.String()
    code = fields.String()
    email = fields.String(allow_none=True)
    phone = fields.String(allow_none=True)
    address = fields.String(allow_none=True)
    city = fields.String(allow_none=True)
    country = fields.String(allow_none=True)
    logo = fields.String(allow_none=True)
    is_active = fields.Boolean()
    created_by = fields.UUID(allow_none=True, dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    users_count = fields.Integer(dump_only=True)
    eleves_count = fields.Integer(dump_only=True)


class PlatformSchoolUpdateSchema(Schema):
    name = fields.String(validate=validate.Length(min=1, max=150))
    email = fields.Email(allow_none=True)
    phone = fields.String(allow_none=True, validate=validate.Length(max=30))
    address = fields.String(allow_none=True)
    city = fields.String(allow_none=True, validate=validate.Length(max=80))
    country = fields.String(allow_none=True, validate=validate.Length(max=80))
    logo = fields.String(allow_none=True)


class OnboardSchoolSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    code = fields.String(required=True, validate=validate.Length(min=2, max=50))
    email = fields.Email(allow_none=True)
    phone = fields.String(allow_none=True)
    address = fields.String(allow_none=True)
    city = fields.String(allow_none=True)
    country = fields.String(allow_none=True)
    logo = fields.String(allow_none=True)
    activate = fields.Boolean(load_default=True)
    admin_nom = fields.String(required=True, validate=validate.Length(min=1, max=100))
    admin_prenom = fields.String(required=True, validate=validate.Length(min=1, max=100))
    admin_email = fields.Email(required=True)
    admin_password = fields.String(required=True, validate=validate.Length(min=8))
    admin_telephone = fields.String(allow_none=True)


class CreateAdminSchema(Schema):
    nom = fields.String(required=True, validate=validate.Length(min=1, max=100))
    prenom = fields.String(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8))
    telephone = fields.String(allow_none=True)


class SchoolContextSchema(Schema):
    school_id = fields.UUID(required=True)


def _school_counts(db, school_id: uuid.UUID) -> dict:
    users_count = db.query(func.count(Utilisateur.id)).filter(Utilisateur.school_id == school_id).scalar() or 0
    eleves_count = db.query(func.count(Eleve.id)).filter(Eleve.school_id == school_id).scalar() or 0
    return {"users_count": int(users_count), "eleves_count": int(eleves_count)}


def _dump_school(school: School, db) -> dict:
    data = PlatformSchoolSchema().dump(school)
    data.update(_school_counts(db, school.id))
    return data


@blp.route("/schools/onboard")
class PlatformSchoolOnboard(MethodView):
    @jwt_required()
    @require_super_admin
    @blp.arguments(OnboardSchoolSchema)
    def post(self, data):
        reject_client_school_id(data)
        actor = get_current_user()
        school, admin, _etab = onboard_school(
            actor=actor,
            name=data["name"],
            code=data["code"],
            email=data.get("email"),
            phone=data.get("phone"),
            address=data.get("address"),
            city=data.get("city"),
            country=data.get("country"),
            logo=data.get("logo"),
            activate=data.get("activate", True),
            admin_nom=data["admin_nom"],
            admin_prenom=data["admin_prenom"],
            admin_email=data["admin_email"],
            admin_password=data["admin_password"],
            admin_telephone=data.get("admin_telephone"),
        )
        db = get_db()
        return (
            jsonify(
                {
                    "school": _dump_school(school, db),
                    "admin": UserSchema().dump(admin),
                }
            ),
            201,
        )


@blp.route("/schools")
class PlatformSchoolsList(MethodView):
    @jwt_required()
    @require_super_admin
    def get(self):
        from flask import request

        db = get_db()
        page, per_page = parse_pagination(default_per_page=50)
        q = db.query(School).order_by(School.name)
        is_active = request.args.get("is_active")
        if is_active is not None and is_active != "":
            q = q.filter(School.is_active.is_(is_active.lower() in ("1", "true", "yes")))
        search = (request.args.get("q") or "").strip()
        if search:
            like = f"%{search}%"
            q = q.filter((School.name.ilike(like)) | (School.code.ilike(like)))
        items, total, pages = paginate_query(q, page, per_page)
        return jsonify(
            pagination_payload(
                [_dump_school(s, db) for s in items],
                page=page,
                per_page=per_page,
                total=total,
                pages=pages,
            )
        )


@blp.route("/schools/<uuid:school_id>")
class PlatformSchoolDetail(MethodView):
    @jwt_required()
    @require_super_admin
    def get(self, school_id):
        db = get_db()
        school = db.query(School).filter(School.id == school_id).first()
        if not school:
            return jsonify({"message": "École introuvable"}), 404
        return jsonify(_dump_school(school, db))

    @jwt_required()
    @require_super_admin
    @blp.arguments(PlatformSchoolUpdateSchema)
    def patch(self, data, school_id):
        reject_client_school_id(data)
        if "code" in data or "is_active" in data:
            return jsonify({"message": "code/is_active non modifiables via PATCH"}), 400
        db = get_db()
        school = db.query(School).filter(School.id == school_id).first()
        if not school:
            return jsonify({"message": "École introuvable"}), 404
        before = {k: getattr(school, k) for k in data}
        for field, value in data.items():
            setattr(school, field, value)
        db.commit()
        actor = get_current_user()
        log_audit(
            "SCHOOL_UPDATED",
            actor.id,
            "schools",
            school.id,
            details={"changed": list(data.keys()), "before": {k: str(before.get(k)) for k in data}},
            school_id=school.id,
        )
        return jsonify(_dump_school(school, db))


@blp.route("/schools/<uuid:school_id>/activate")
class PlatformSchoolActivate(MethodView):
    @jwt_required()
    @require_super_admin
    def post(self, school_id):
        db = get_db()
        school = db.query(School).filter(School.id == school_id).first()
        if not school:
            return jsonify({"message": "École introuvable"}), 404
        if school.is_active:
            return jsonify(_dump_school(school, db))
        school.is_active = True
        db.commit()
        actor = get_current_user()
        log_audit("SCHOOL_ACTIVATED", actor.id, "schools", school.id, school_id=school.id)
        return jsonify(_dump_school(school, db))


@blp.route("/schools/<uuid:school_id>/deactivate")
class PlatformSchoolDeactivate(MethodView):
    @jwt_required()
    @require_super_admin
    def post(self, school_id):
        db = get_db()
        school = db.query(School).filter(School.id == school_id).first()
        if not school:
            return jsonify({"message": "École introuvable"}), 404
        if not school.is_active:
            return jsonify(_dump_school(school, db))
        school.is_active = False
        db.commit()
        actor = get_current_user()
        log_audit("SCHOOL_DEACTIVATED", actor.id, "schools", school.id, school_id=school.id)
        return jsonify(_dump_school(school, db))


@blp.route("/schools/<uuid:school_id>/users")
class PlatformSchoolUsers(MethodView):
    @jwt_required()
    @require_super_admin
    def get(self, school_id):
        db = get_db()
        school = db.query(School).filter(School.id == school_id).first()
        if not school:
            return jsonify({"message": "École introuvable"}), 404
        page, per_page = parse_pagination(default_per_page=50)
        q = (
            db.query(Utilisateur)
            .filter(Utilisateur.school_id == school_id)
            .order_by(Utilisateur.nom, Utilisateur.prenom)
        )
        items, total, pages = paginate_query(q, page, per_page)
        return jsonify(
            pagination_payload(
                [UserSchema().dump(u) for u in items],
                page=page,
                per_page=per_page,
                total=total,
                pages=pages,
            )
        )


@blp.route("/schools/<uuid:school_id>/admins")
class PlatformSchoolAdmins(MethodView):
    @jwt_required()
    @require_super_admin
    @blp.arguments(CreateAdminSchema)
    def post(self, data, school_id):
        reject_client_school_id(data)
        db = get_db()
        school = db.query(School).filter(School.id == school_id).first()
        if not school:
            return jsonify({"message": "École introuvable"}), 404
        actor = get_current_user()
        admin = create_school_admin(
            actor=actor,
            school=school,
            nom=data["nom"],
            prenom=data["prenom"],
            email=data["email"],
            password=data["password"],
            telephone=data.get("telephone"),
        )
        return UserSchema().dump(admin), 201


@blp.route("/context/school")
class PlatformSchoolContext(MethodView):
    @jwt_required()
    @require_super_admin
    @blp.arguments(SchoolContextSchema)
    def put(self, data):
        """Entrer dans le contexte d'une école (re-issue access token)."""
        db = get_db()
        school = db.query(School).filter(School.id == data["school_id"]).first()
        if not school:
            return jsonify({"message": "École introuvable"}), 404
        user = get_current_user()
        access_token = build_access_token_for_user(user, acting_school_id=school.id)
        log_audit(
            "SCHOOL_CONTEXT_ENTER",
            user.id,
            "schools",
            school.id,
            details={"school_code": school.code},
            school_id=school.id,
        )
        return jsonify(
            {
                "access_token": access_token,
                "acting_school": PlatformSchoolSchema().dump(school),
            }
        ), 200

    @jwt_required()
    @require_super_admin
    def delete(self):
        """Quitter le contexte école (access token sans acting_school_id)."""
        user = get_current_user()
        claims = get_jwt() or {}
        previous = claims.get("acting_school_id")
        access_token = build_access_token_for_user(user, acting_school_id=None)
        prev_uuid = None
        if previous:
            try:
                prev_uuid = uuid.UUID(str(previous))
            except ValueError:
                prev_uuid = None
        log_audit(
            "SCHOOL_CONTEXT_EXIT",
            user.id,
            "schools",
            prev_uuid,
            details={"previous_acting_school_id": previous},
            school_id=prev_uuid,
            allow_null_school=prev_uuid is None,
        )
        return jsonify({"access_token": access_token, "acting_school": None}), 200
