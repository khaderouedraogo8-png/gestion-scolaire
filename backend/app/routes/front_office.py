"""Front office — visiteurs et sorties élèves."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import Eleve, SortieEleve, Visiteur
from app.services.tenant import (
    apply_tenant_school,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)

blp = Blueprint("front_office", __name__, description="Front office / accueil")

_STAFF = ("administrateur", "directeur", "secretariat")


class VisiteurSchema(Schema):
    id = fields.UUID(dump_only=True)
    nom = fields.String(required=True)
    prenom = fields.String(allow_none=True)
    motif = fields.String(allow_none=True)
    piece_identite = fields.String(allow_none=True)
    telephone = fields.String(allow_none=True)
    heure_entree = fields.DateTime(dump_only=True)
    heure_sortie = fields.DateTime(dump_only=True, allow_none=True)
    accueilli_par = fields.UUID(dump_only=True, allow_none=True)
    id_eleve_visite = fields.UUID(allow_none=True)


class SortieSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    date_sortie = fields.DateTime(dump_only=True)
    motif = fields.String(allow_none=True)
    autorise_par = fields.UUID(dump_only=True, allow_none=True)
    recupere_par = fields.String(allow_none=True)
    heure_retour = fields.DateTime(dump_only=True, allow_none=True)
    statut = fields.String(load_default="sorti")


@blp.route("/visiteurs")
class VisiteursResource(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        q = tenant_query(Visiteur).order_by(Visiteur.heure_entree.desc())
        ouverts = request.args.get("ouverts")
        if ouverts in ("1", "true", "oui"):
            q = q.filter(Visiteur.heure_sortie.is_(None))
        return jsonify(VisiteurSchema(many=True).dump(q.limit(200).all()))

    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(VisiteurSchema)
    @blp.response(201, VisiteurSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        if data.get("id_eleve_visite"):
            get_or_404_tenant(Eleve, data["id_eleve_visite"])
        row = Visiteur(id=uuid.uuid4(), accueilli_par=user.id, **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/visiteurs/<uuid:id_visiteur>/sortie")
class VisiteurSortie(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def post(self, id_visiteur):
        db = get_db()
        row = get_or_404_tenant(Visiteur, id_visiteur)
        if row.heure_sortie:
            return jsonify({"message": "Déjà sorti"}), 400
        row.heure_sortie = datetime.now(UTC)
        db.commit()
        return jsonify(VisiteurSchema().dump(row))


@blp.route("/sorties")
class SortiesResource(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        q = tenant_query(SortieEleve).order_by(SortieEleve.date_sortie.desc())
        id_eleve = request.args.get("id_eleve")
        if id_eleve:
            q = q.filter(SortieEleve.id_eleve == uuid.UUID(id_eleve))
        return jsonify(SortieSchema(many=True).dump(q.limit(200).all()))

    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(SortieSchema)
    @blp.response(201, SortieSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        get_or_404_tenant(Eleve, data["id_eleve"])
        row = SortieEleve(id=uuid.uuid4(), autorise_par=user.id, **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/sorties/<uuid:id_sortie>/retour")
class SortieRetour(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def post(self, id_sortie):
        db = get_db()
        row = get_or_404_tenant(SortieEleve, id_sortie)
        row.heure_retour = datetime.now(UTC)
        row.statut = "revenu"
        db.commit()
        return jsonify(SortieSchema().dump(row))
