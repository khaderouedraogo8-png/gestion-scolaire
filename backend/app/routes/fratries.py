"""Fratries et règles de remise."""
from __future__ import annotations

import uuid

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields, validate

from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import Eleve, EleveFratrie, Fratrie, RemiseRegle
from app.services.tenant import (
    apply_tenant_school,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)

blp = Blueprint("fratries", __name__, description="Fratries et remises")


class FratrieSchema(Schema):
    id = fields.UUID(dump_only=True)
    libelle = fields.String(allow_none=True)
    id_parent_principal = fields.UUID(allow_none=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class LinkEleveSchema(Schema):
    id_eleve = fields.UUID(required=True)


class RemiseRegleSchema(Schema):
    id = fields.UUID(dump_only=True)
    code = fields.String(required=True)
    libelle = fields.String(required=True)
    type_remise = fields.String(load_default="pourcent", validate=validate.OneOf(["pourcent", "montant"]))
    valeur = fields.Decimal(as_string=True, required=True)
    condition_type = fields.String(allow_none=True)
    condition_valeur = fields.String(allow_none=True)
    actif = fields.Boolean(load_default=True)
    priorite = fields.Integer(load_default=0)
    created_at = fields.DateTime(dump_only=True)


def _dump_fratrie(f: Fratrie, eleves=None) -> dict:
    data = FratrieSchema().dump(f)
    if eleves is not None:
        data["eleves"] = eleves
    return data


@blp.route("/")
class FratriesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "agent_comptable")
    def get(self):
        rows = tenant_query(Fratrie).order_by(Fratrie.created_at.desc()).all()
        out = []
        for f in rows:
            links = tenant_query(EleveFratrie).filter(EleveFratrie.id_fratrie == f.id).all()
            eleves = []
            for link in links:
                e = tenant_query(Eleve).filter(Eleve.id == link.id_eleve).first()
                if e:
                    eleves.append({
                        "id": str(e.id),
                        "matricule": e.matricule,
                        "nom": e.nom,
                        "prenom": e.prenom,
                    })
            out.append(_dump_fratrie(f, eleves))
        return jsonify(out)

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(FratrieSchema)
    @blp.response(201, FratrieSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        fratrie = Fratrie(id=uuid.uuid4(), **data)
        apply_tenant_school(fratrie)
        db.add(fratrie)
        db.commit()
        return fratrie, 201


@blp.route("/<uuid:id_fratrie>")
class FratrieDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "agent_comptable")
    def get(self, id_fratrie):
        f = get_or_404_tenant(Fratrie, id_fratrie)
        links = tenant_query(EleveFratrie).filter(EleveFratrie.id_fratrie == f.id).all()
        eleves = []
        for link in links:
            e = tenant_query(Eleve).filter(Eleve.id == link.id_eleve).first()
            if e:
                eleves.append({
                    "id": str(e.id),
                    "matricule": e.matricule,
                    "nom": e.nom,
                    "prenom": e.prenom,
                })
        return jsonify(_dump_fratrie(f, eleves))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(FratrieSchema(partial=True))
    def put(self, data, id_fratrie):
        db = get_db()
        f = get_or_404_tenant(Fratrie, id_fratrie)
        for k, v in data.items():
            setattr(f, k, v)
        db.commit()
        return jsonify(_dump_fratrie(f))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def delete(self, id_fratrie):
        db = get_db()
        f = get_or_404_tenant(Fratrie, id_fratrie)
        db.delete(f)
        db.commit()
        return jsonify({"message": "Fratrie supprimée"})


@blp.route("/<uuid:id_fratrie>/eleves")
class FratrieLinkEleve(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(LinkEleveSchema)
    def post(self, data, id_fratrie):
        db = get_db()
        get_or_404_tenant(Fratrie, id_fratrie)
        get_or_404_tenant(Eleve, data["id_eleve"])
        existing = (
            tenant_query(EleveFratrie)
            .filter(
                EleveFratrie.id_fratrie == id_fratrie,
                EleveFratrie.id_eleve == data["id_eleve"],
            )
            .first()
        )
        if existing:
            return jsonify({"message": "Déjà lié", "id": str(existing.id)}), 200
        link = EleveFratrie(id=uuid.uuid4(), id_fratrie=id_fratrie, id_eleve=data["id_eleve"])
        apply_tenant_school(link)
        db.add(link)
        db.commit()
        return jsonify({"id": str(link.id), "id_eleve": str(data["id_eleve"])}), 201


@blp.route("/<uuid:id_fratrie>/eleves/<uuid:id_eleve>")
class FratrieUnlinkEleve(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def delete(self, id_fratrie, id_eleve):
        db = get_db()
        get_or_404_tenant(Fratrie, id_fratrie)
        link = (
            tenant_query(EleveFratrie)
            .filter(EleveFratrie.id_fratrie == id_fratrie, EleveFratrie.id_eleve == id_eleve)
            .first()
        )
        if not link:
            return jsonify({"message": "Lien introuvable"}), 404
        db.delete(link)
        db.commit()
        return jsonify({"message": "Élève détaché"})


@blp.route("/remises")
class RemisesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable", "secretariat")
    def get(self):
        rows = tenant_query(RemiseRegle).order_by(RemiseRegle.priorite.desc()).all()
        return jsonify(RemiseRegleSchema(many=True).dump(rows))

    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(RemiseRegleSchema)
    @blp.response(201, RemiseRegleSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        regle = RemiseRegle(id=uuid.uuid4(), **data)
        apply_tenant_school(regle)
        db.add(regle)
        db.commit()
        return regle, 201


@blp.route("/remises/<uuid:id_regle>")
class RemiseDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(RemiseRegleSchema(partial=True))
    def put(self, data, id_regle):
        db = get_db()
        regle = get_or_404_tenant(RemiseRegle, id_regle)
        for k, v in data.items():
            setattr(regle, k, v)
        db.commit()
        return jsonify(RemiseRegleSchema().dump(regle))

    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    def delete(self, id_regle):
        db = get_db()
        regle = get_or_404_tenant(RemiseRegle, id_regle)
        db.delete(regle)
        db.commit()
        return jsonify({"message": "Règle supprimée"})
