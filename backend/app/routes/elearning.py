"""E-learning — devoirs, remises, quiz."""
from __future__ import annotations

import uuid

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import ElearningDevoir, ElearningQuiz, ElearningRemise, Eleve
from app.services.tenant import (
    apply_tenant_school,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)

blp = Blueprint("elearning", __name__, description="E-learning")


class DevoirSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_classe = fields.UUID(allow_none=True)
    id_matiere = fields.UUID(allow_none=True)
    titre = fields.String(required=True)
    consignes = fields.String(allow_none=True)
    date_limite = fields.DateTime(allow_none=True)
    cree_par = fields.UUID(dump_only=True, allow_none=True)
    publie = fields.Boolean(load_default=True)
    created_at = fields.DateTime(dump_only=True)


class RemiseSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_devoir = fields.UUID(required=True)
    id_eleve = fields.UUID(required=True)
    fichier_url = fields.String(allow_none=True)
    contenu = fields.String(allow_none=True)
    date_remise = fields.DateTime(dump_only=True)
    note = fields.Decimal(as_string=True, allow_none=True)
    commentaire = fields.String(allow_none=True)


class QuizSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_classe = fields.UUID(allow_none=True)
    id_matiere = fields.UUID(allow_none=True)
    titre = fields.String(required=True)
    questions = fields.Raw(allow_none=True)
    duree_minutes = fields.Integer(allow_none=True)
    publie = fields.Boolean(load_default=False)
    cree_par = fields.UUID(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


@blp.route("/devoirs")
class DevoirsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant", "secretariat", "parent")
    def get(self):
        q = tenant_query(ElearningDevoir)
        id_classe = request.args.get("id_classe")
        if id_classe:
            q = q.filter(ElearningDevoir.id_classe == uuid.UUID(id_classe))
        return jsonify(DevoirSchema(many=True).dump(q.order_by(ElearningDevoir.created_at.desc()).all()))

    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    @blp.arguments(DevoirSchema)
    @blp.response(201, DevoirSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        row = ElearningDevoir(id=uuid.uuid4(), cree_par=user.id, **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/devoirs/<uuid:id_devoir>")
class DevoirDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant", "secretariat")
    def get(self, id_devoir):
        return jsonify(DevoirSchema().dump(get_or_404_tenant(ElearningDevoir, id_devoir)))

    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    @blp.arguments(DevoirSchema(partial=True))
    def put(self, data, id_devoir):
        db = get_db()
        row = get_or_404_tenant(ElearningDevoir, id_devoir)
        for k, v in data.items():
            setattr(row, k, v)
        db.commit()
        return jsonify(DevoirSchema().dump(row))

    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    def delete(self, id_devoir):
        db = get_db()
        row = get_or_404_tenant(ElearningDevoir, id_devoir)
        db.delete(row)
        db.commit()
        return jsonify({"message": "Devoir supprimé"})


@blp.route("/remises")
class RemisesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant", "parent", "secretariat")
    def get(self):
        q = tenant_query(ElearningRemise)
        id_devoir = request.args.get("id_devoir")
        id_eleve = request.args.get("id_eleve")
        if id_devoir:
            q = q.filter(ElearningRemise.id_devoir == uuid.UUID(id_devoir))
        if id_eleve:
            q = q.filter(ElearningRemise.id_eleve == uuid.UUID(id_eleve))
        return jsonify(RemiseSchema(many=True).dump(q.all()))

    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant", "parent", "secretariat")
    @blp.arguments(RemiseSchema)
    @blp.response(201, RemiseSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        get_or_404_tenant(ElearningDevoir, data["id_devoir"])
        get_or_404_tenant(Eleve, data["id_eleve"])
        existing = (
            tenant_query(ElearningRemise)
            .filter(
                ElearningRemise.id_devoir == data["id_devoir"],
                ElearningRemise.id_eleve == data["id_eleve"],
            )
            .first()
        )
        if existing:
            for k, v in data.items():
                if k not in ("id_devoir", "id_eleve"):
                    setattr(existing, k, v)
            db.commit()
            return jsonify(RemiseSchema().dump(existing)), 200
        row = ElearningRemise(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/remises/<uuid:id_remise>")
class RemiseDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    @blp.arguments(RemiseSchema(partial=True))
    def put(self, data, id_remise):
        """Noter / commenter une remise."""
        db = get_db()
        row = get_or_404_tenant(ElearningRemise, id_remise)
        for k, v in data.items():
            if k not in ("id_devoir", "id_eleve"):
                setattr(row, k, v)
        db.commit()
        return jsonify(RemiseSchema().dump(row))


@blp.route("/quiz")
class QuizResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant", "parent", "secretariat")
    def get(self):
        q = tenant_query(ElearningQuiz)
        id_classe = request.args.get("id_classe")
        if id_classe:
            q = q.filter(ElearningQuiz.id_classe == uuid.UUID(id_classe))
        return jsonify(QuizSchema(many=True).dump(q.order_by(ElearningQuiz.created_at.desc()).all()))

    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    @blp.arguments(QuizSchema)
    @blp.response(201, QuizSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        row = ElearningQuiz(id=uuid.uuid4(), cree_par=user.id, **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/quiz/<uuid:id_quiz>")
class QuizDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    @blp.arguments(QuizSchema(partial=True))
    def put(self, data, id_quiz):
        db = get_db()
        row = get_or_404_tenant(ElearningQuiz, id_quiz)
        for k, v in data.items():
            setattr(row, k, v)
        db.commit()
        return jsonify(QuizSchema().dump(row))

    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    def delete(self, id_quiz):
        db = get_db()
        row = get_or_404_tenant(ElearningQuiz, id_quiz)
        db.delete(row)
        db.commit()
        return jsonify({"message": "Quiz supprimé"})
