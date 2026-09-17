"""RH — contrats et congés."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import RhConge, RhContrat
from app.services.tenant import (
    apply_tenant_school,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)

blp = Blueprint("rh", __name__, description="Ressources humaines")


class ContratSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_utilisateur = fields.UUID(allow_none=True)
    id_enseignant = fields.UUID(allow_none=True)
    type_contrat = fields.String(required=True)
    date_debut = fields.Date(required=True)
    date_fin = fields.Date(allow_none=True)
    salaire_base = fields.Decimal(as_string=True, allow_none=True)
    statut = fields.String(load_default="actif")
    poste = fields.String(allow_none=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class CongeSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_utilisateur = fields.UUID(required=True)
    type_conge = fields.String(required=True)
    date_debut = fields.Date(required=True)
    date_fin = fields.Date(required=True)
    statut = fields.String(load_default="demande")
    motif = fields.String(allow_none=True)
    valide_par = fields.UUID(dump_only=True, allow_none=True)
    valide_le = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class CongeStatutSchema(Schema):
    statut = fields.String(required=True)


@blp.route("/contrats")
class ContratsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def get(self):
        q = tenant_query(RhContrat)
        statut = request.args.get("statut")
        if statut:
            q = q.filter(RhContrat.statut == statut)
        return jsonify(ContratSchema(many=True).dump(q.order_by(RhContrat.date_debut.desc()).all()))

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(ContratSchema)
    @blp.response(201, ContratSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        row = RhContrat(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/contrats/alertes-expiration")
class ContratsAlertesExpiration(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def get(self):
        """Contrats actifs expirant dans les N jours (défaut 30)."""
        jours = request.args.get("jours", default=30, type=int)
        jours = max(1, min(jours or 30, 365))
        today = date.today()
        until = today + timedelta(days=jours)
        rows = (
            tenant_query(RhContrat)
            .filter(
                RhContrat.statut == "actif",
                RhContrat.date_fin.isnot(None),
                RhContrat.date_fin >= today,
                RhContrat.date_fin <= until,
            )
            .order_by(RhContrat.date_fin.asc())
            .all()
        )
        payload = []
        for c in rows:
            item = ContratSchema().dump(c)
            item["jours_restants"] = (c.date_fin - today).days if c.date_fin else None
            payload.append(item)
        return jsonify({
            "alertes": payload,
            "nb": len(payload),
            "jours": jours,
            "jusqu_au": until.isoformat(),
        })


@blp.route("/contrats/<uuid:id_contrat>")
class ContratDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def get(self, id_contrat):
        return jsonify(ContratSchema().dump(get_or_404_tenant(RhContrat, id_contrat)))

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(ContratSchema(partial=True))
    def put(self, data, id_contrat):
        db = get_db()
        row = get_or_404_tenant(RhContrat, id_contrat)
        for k, v in data.items():
            setattr(row, k, v)
        db.commit()
        return jsonify(ContratSchema().dump(row))

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_contrat):
        db = get_db()
        row = get_or_404_tenant(RhContrat, id_contrat)
        db.delete(row)
        db.commit()
        return jsonify({"message": "Contrat supprimé"})


@blp.route("/conges")
class CongesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def get(self):
        q = tenant_query(RhConge)
        statut = request.args.get("statut")
        if statut:
            q = q.filter(RhConge.statut == statut)
        return jsonify(CongeSchema(many=True).dump(q.order_by(RhConge.date_debut.desc()).all()))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(CongeSchema)
    @blp.response(201, CongeSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        row = RhConge(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/conges/<uuid:id_conge>")
class CongeDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(CongeSchema(partial=True))
    def put(self, data, id_conge):
        db = get_db()
        row = get_or_404_tenant(RhConge, id_conge)
        for k, v in data.items():
            setattr(row, k, v)
        db.commit()
        return jsonify(CongeSchema().dump(row))

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_conge):
        db = get_db()
        row = get_or_404_tenant(RhConge, id_conge)
        db.delete(row)
        db.commit()
        return jsonify({"message": "Congé supprimé"})


@blp.route("/conges/<uuid:id_conge>/statut")
class CongeStatut(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(CongeStatutSchema)
    def patch(self, data, id_conge):
        db = get_db()
        user = get_current_user()
        row = get_or_404_tenant(RhConge, id_conge)
        row.statut = data["statut"]
        if data["statut"] in ("approuve", "refuse"):
            row.valide_par = user.id
            row.valide_le = datetime.now(UTC)
        db.commit()
        return jsonify(CongeSchema().dump(row))
