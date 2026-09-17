"""Admissions — dossiers, funnel statut, conversion élève."""
from __future__ import annotations

import uuid
from datetime import date

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields, validate

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import AdmissionDossier, AnneeScolaire, Eleve, Etablissement, Inscription
from app.services.tenant import (
    apply_tenant_school,
    get_current_school_id,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)

blp = Blueprint("admission", __name__, description="Admissions / dossiers")

STATUTS = (
    "brouillon",
    "soumis",
    "en_examen",
    "accepte",
    "refuse",
    "liste_attente",
    "inscrit",
)


class AdmissionDossierSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_annee = fields.UUID(allow_none=True)
    nom = fields.String(required=True)
    prenom = fields.String(required=True)
    sexe = fields.String(allow_none=True)
    date_naissance = fields.Date(allow_none=True)
    lieu_naissance = fields.String(allow_none=True)
    telephone_parent = fields.String(allow_none=True)
    email_parent = fields.String(allow_none=True)
    niveau_demande = fields.String(allow_none=True)
    statut = fields.String(load_default="brouillon", validate=validate.OneOf(STATUTS))
    pieces = fields.Dict(allow_none=True)
    id_eleve = fields.UUID(dump_only=True, allow_none=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class StatutPatchSchema(Schema):
    statut = fields.String(required=True, validate=validate.OneOf(STATUTS))


class ConvertSchema(Schema):
    id_classe = fields.UUID(required=True)
    id_annee = fields.UUID(allow_none=True)
    matricule = fields.String(allow_none=True)


def _dump(d: AdmissionDossier) -> dict:
    return AdmissionDossierSchema().dump(d)


def _generer_matricule(db, id_annee: uuid.UUID | None) -> str:
    school_id = get_current_school_id()
    etab = db.query(Etablissement).filter(Etablissement.school_id == school_id).first()
    annee = get_or_404_tenant(AnneeScolaire, id_annee) if id_annee else None
    format_str = (etab.format_matricule if etab else None) or "{ANNEE}M-{SEQ}"
    annee_court = annee.libelle[:4] if annee else str(date.today().year)
    count = tenant_query(Eleve).count() + 1
    return format_str.replace("{ANNEE}", annee_court).replace("{SEQ}", str(count).zfill(3))


@blp.route("/")
class DossiersResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def get(self):
        q = tenant_query(AdmissionDossier)
        statut = request.args.get("statut")
        if statut:
            q = q.filter(AdmissionDossier.statut == statut)
        id_annee = request.args.get("id_annee")
        if id_annee:
            q = q.filter(AdmissionDossier.id_annee == uuid.UUID(id_annee))
        rows = q.order_by(AdmissionDossier.created_at.desc()).all()
        return jsonify([_dump(r) for r in rows])

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(AdmissionDossierSchema)
    @blp.response(201, AdmissionDossierSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        if data.get("id_annee"):
            get_or_404_tenant(AnneeScolaire, data["id_annee"])
        dossier = AdmissionDossier(id=uuid.uuid4(), **data)
        apply_tenant_school(dossier)
        db.add(dossier)
        db.commit()
        return dossier, 201


@blp.route("/<uuid:id_dossier>")
class DossierDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def get(self, id_dossier):
        return jsonify(_dump(get_or_404_tenant(AdmissionDossier, id_dossier)))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(AdmissionDossierSchema(partial=True))
    def put(self, data, id_dossier):
        db = get_db()
        dossier = get_or_404_tenant(AdmissionDossier, id_dossier)
        for k, v in data.items():
            if k not in ("id_eleve",):
                setattr(dossier, k, v)
        db.commit()
        return jsonify(_dump(dossier))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def delete(self, id_dossier):
        db = get_db()
        dossier = get_or_404_tenant(AdmissionDossier, id_dossier)
        db.delete(dossier)
        db.commit()
        return jsonify({"message": "Dossier supprimé"})


@blp.route("/<uuid:id_dossier>/statut")
class DossierStatut(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(StatutPatchSchema)
    def patch(self, data, id_dossier):
        db = get_db()
        dossier = get_or_404_tenant(AdmissionDossier, id_dossier)
        dossier.statut = data["statut"]
        db.commit()
        return jsonify(_dump(dossier))


@blp.route("/<uuid:id_dossier>/convert-to-eleve")
class DossierConvert(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(ConvertSchema)
    def post(self, data, id_dossier):
        """Crée un élève + inscription à partir d'un dossier accepté."""
        from app.models import Classe

        db = get_db()
        user = get_current_user()
        dossier = get_or_404_tenant(AdmissionDossier, id_dossier)
        if dossier.id_eleve:
            return jsonify({"message": "Déjà converti", "id_eleve": str(dossier.id_eleve)}), 409
        if dossier.statut not in ("accepte", "liste_attente"):
            return jsonify({"message": "Le dossier doit être accepté avant conversion"}), 400

        id_classe = data["id_classe"]
        classe = get_or_404_tenant(Classe, id_classe)
        id_annee = data.get("id_annee") or dossier.id_annee
        if not id_annee:
            annee = tenant_query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
            if not annee:
                return jsonify({"message": "id_annee requis"}), 400
            id_annee = annee.id
        else:
            get_or_404_tenant(AnneeScolaire, id_annee)

        matricule = data.get("matricule") or _generer_matricule(db, id_annee)
        eleve = Eleve(
            id=uuid.uuid4(),
            matricule=matricule,
            nom=dossier.nom,
            prenom=dossier.prenom,
            sexe=dossier.sexe,
            date_naissance=dossier.date_naissance,
            lieu_naissance=dossier.lieu_naissance,
            pieces_justificatives=dossier.pieces,
        )
        apply_tenant_school(eleve)
        db.add(eleve)
        db.flush()

        insc = Inscription(
            id=uuid.uuid4(),
            id_eleve=eleve.id,
            id_classe=classe.id,
            id_annee=id_annee,
            statut="inscrit",
            date_inscription=date.today(),
        )
        apply_tenant_school(insc)
        db.add(insc)

        dossier.id_eleve = eleve.id
        dossier.statut = "inscrit"
        db.commit()
        return jsonify({
            "id_eleve": str(eleve.id),
            "matricule": eleve.matricule,
            "id_inscription": str(insc.id),
            "dossier": _dump(dossier),
            "converted_by": str(user.id),
        }), 201
