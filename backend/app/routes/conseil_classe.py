"""Conseil de classe — sessions et décisions de passage."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields, validate

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import AnneeScolaire, Classe, ConseilClasseSession, DecisionPassage, Eleve
from app.services.tenant import (
    apply_tenant_school,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)

blp = Blueprint("conseil_classe", __name__, description="Conseil de classe")

DECISIONS = ("passe", "redouble", "oriente", "exclu", "ajourne", "autre")


class SessionSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_classe = fields.UUID(required=True)
    id_trimestre = fields.UUID(allow_none=True)
    id_annee = fields.UUID(allow_none=True)
    date_session = fields.Date(required=True)
    statut = fields.String(load_default="planifie")
    pv_url = fields.String(allow_none=True)
    notes = fields.String(allow_none=True)
    anime_par = fields.UUID(allow_none=True, dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class DecisionSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)
    id_session = fields.UUID(allow_none=True)
    decision = fields.String(required=True, validate=validate.OneOf(DECISIONS))
    mention = fields.String(allow_none=True)
    commentaire = fields.String(allow_none=True)
    valide_par = fields.UUID(dump_only=True, allow_none=True)
    valide_le = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


@blp.route("/sessions")
class SessionsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        q = tenant_query(ConseilClasseSession)
        id_classe = request.args.get("id_classe")
        if id_classe:
            q = q.filter(ConseilClasseSession.id_classe == uuid.UUID(id_classe))
        rows = q.order_by(ConseilClasseSession.date_session.desc()).all()
        return jsonify(SessionSchema(many=True).dump(rows))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(SessionSchema)
    @blp.response(201, SessionSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        get_or_404_tenant(Classe, data["id_classe"])
        if data.get("id_annee"):
            get_or_404_tenant(AnneeScolaire, data["id_annee"])
        session = ConseilClasseSession(id=uuid.uuid4(), anime_par=user.id, **data)
        apply_tenant_school(session)
        db.add(session)
        db.commit()
        return session, 201


@blp.route("/sessions/<uuid:id_session>")
class SessionDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self, id_session):
        return jsonify(SessionSchema().dump(get_or_404_tenant(ConseilClasseSession, id_session)))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(SessionSchema(partial=True))
    def put(self, data, id_session):
        db = get_db()
        session = get_or_404_tenant(ConseilClasseSession, id_session)
        for k, v in data.items():
            setattr(session, k, v)
        db.commit()
        return jsonify(SessionSchema().dump(session))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def delete(self, id_session):
        db = get_db()
        session = get_or_404_tenant(ConseilClasseSession, id_session)
        db.delete(session)
        db.commit()
        return jsonify({"message": "Session supprimée"})


@blp.route("/decisions")
class DecisionsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        q = tenant_query(DecisionPassage)
        id_eleve = request.args.get("id_eleve")
        id_annee = request.args.get("id_annee")
        id_session = request.args.get("id_session")
        if id_eleve:
            q = q.filter(DecisionPassage.id_eleve == uuid.UUID(id_eleve))
        if id_annee:
            q = q.filter(DecisionPassage.id_annee == uuid.UUID(id_annee))
        if id_session:
            q = q.filter(DecisionPassage.id_session == uuid.UUID(id_session))
        rows = q.order_by(DecisionPassage.created_at.desc()).all()
        return jsonify(DecisionSchema(many=True).dump(rows))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(DecisionSchema)
    @blp.response(201, DecisionSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        get_or_404_tenant(Eleve, data["id_eleve"])
        get_or_404_tenant(AnneeScolaire, data["id_annee"])
        if data.get("id_session"):
            get_or_404_tenant(ConseilClasseSession, data["id_session"])
        existing = (
            tenant_query(DecisionPassage)
            .filter(
                DecisionPassage.id_eleve == data["id_eleve"],
                DecisionPassage.id_annee == data["id_annee"],
            )
            .first()
        )
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            existing.valide_par = user.id
            existing.valide_le = datetime.now(UTC)
            db.commit()
            return jsonify(DecisionSchema().dump(existing)), 200
        decision = DecisionPassage(
            id=uuid.uuid4(),
            valide_par=user.id,
            valide_le=datetime.now(UTC),
            **data,
        )
        apply_tenant_school(decision)
        db.add(decision)
        db.commit()
        return decision, 201


@blp.route("/decisions/<uuid:id_decision>")
class DecisionDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(DecisionSchema(partial=True))
    def put(self, data, id_decision):
        db = get_db()
        user = get_current_user()
        decision = get_or_404_tenant(DecisionPassage, id_decision)
        for k, v in data.items():
            setattr(decision, k, v)
        decision.valide_par = user.id
        decision.valide_le = datetime.now(UTC)
        db.commit()
        return jsonify(DecisionSchema().dump(decision))

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_decision):
        db = get_db()
        decision = get_or_404_tenant(DecisionPassage, id_decision)
        db.delete(decision)
        db.commit()
        return jsonify({"message": "Décision supprimée"})
