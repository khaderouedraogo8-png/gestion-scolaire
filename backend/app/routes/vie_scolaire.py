"""Vie scolaire — cantine, transport, internat, infirmière, bibliothèque."""
from __future__ import annotations

import uuid
from datetime import date

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import (
    BibliothequeLivre,
    BibliothequePret,
    CantineAbonnement,
    CantinePresence,
    Eleve,
    InfirmiereSoin,
    InternatAffectation,
    InternatChambre,
    TransportArret,
    TransportEleve,
    TransportItineraire,
)
from app.services.tenant import (
    apply_tenant_school,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)

blp = Blueprint("vie_scolaire", __name__, description="Vie scolaire")

_STAFF = ("administrateur", "directeur", "secretariat")


# ---- Cantine ----


class CantineAbonnementSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    id_annee = fields.UUID(allow_none=True)
    formule = fields.String(load_default="standard")
    montant = fields.Decimal(as_string=True, allow_none=True)
    date_debut = fields.Date(required=True)
    date_fin = fields.Date(allow_none=True)
    actif = fields.Boolean(load_default=True)
    created_at = fields.DateTime(dump_only=True)


class CantinePresenceSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    date_presence = fields.Date(required=True)
    repas = fields.String(load_default="midi")
    present = fields.Boolean(load_default=True)
    notes = fields.String(allow_none=True)


@blp.route("/cantine/abonnements")
class CantineAbonnements(MethodView):
    @jwt_required()
    @require_role(*_STAFF, "agent_comptable")
    def get(self):
        q = tenant_query(CantineAbonnement)
        id_eleve = request.args.get("id_eleve")
        if id_eleve:
            q = q.filter(CantineAbonnement.id_eleve == uuid.UUID(id_eleve))
        return jsonify(CantineAbonnementSchema(many=True).dump(q.all()))

    @jwt_required()
    @require_role(*_STAFF, "agent_comptable")
    @blp.arguments(CantineAbonnementSchema)
    @blp.response(201, CantineAbonnementSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        get_or_404_tenant(Eleve, data["id_eleve"])
        row = CantineAbonnement(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/cantine/presences")
class CantinePresences(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        q = tenant_query(CantinePresence)
        date_p = request.args.get("date")
        if date_p:
            q = q.filter(CantinePresence.date_presence == date_p)
        return jsonify(CantinePresenceSchema(many=True).dump(q.all()))

    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(CantinePresenceSchema)
    @blp.response(201, CantinePresenceSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        get_or_404_tenant(Eleve, data["id_eleve"])
        row = CantinePresence(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


# ---- Transport ----


class ItineraireSchema(Schema):
    id = fields.UUID(dump_only=True)
    libelle = fields.String(required=True)
    description = fields.String(allow_none=True)
    actif = fields.Boolean(load_default=True)
    created_at = fields.DateTime(dump_only=True)


class ArretSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_itineraire = fields.UUID(required=True)
    libelle = fields.String(required=True)
    ordre = fields.Integer(load_default=0)
    heure_passage = fields.String(allow_none=True)
    latitude = fields.Decimal(as_string=True, allow_none=True)
    longitude = fields.Decimal(as_string=True, allow_none=True)


class TransportEleveSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    id_itineraire = fields.UUID(required=True)
    id_arret = fields.UUID(allow_none=True)
    id_annee = fields.UUID(allow_none=True)
    actif = fields.Boolean(load_default=True)
    created_at = fields.DateTime(dump_only=True)


@blp.route("/transport/itineraires")
class TransportItineraires(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        return jsonify(ItineraireSchema(many=True).dump(tenant_query(TransportItineraire).all()))

    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(ItineraireSchema)
    @blp.response(201, ItineraireSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        row = TransportItineraire(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/transport/arrets")
class TransportArrets(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        q = tenant_query(TransportArret)
        id_itineraire = request.args.get("id_itineraire")
        if id_itineraire:
            q = q.filter(TransportArret.id_itineraire == uuid.UUID(id_itineraire))
        return jsonify(ArretSchema(many=True).dump(q.order_by(TransportArret.ordre).all()))

    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(ArretSchema)
    @blp.response(201, ArretSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        get_or_404_tenant(TransportItineraire, data["id_itineraire"])
        row = TransportArret(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/transport/eleves")
class TransportEleves(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        return jsonify(TransportEleveSchema(many=True).dump(tenant_query(TransportEleve).all()))

    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(TransportEleveSchema)
    @blp.response(201, TransportEleveSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        get_or_404_tenant(Eleve, data["id_eleve"])
        get_or_404_tenant(TransportItineraire, data["id_itineraire"])
        row = TransportEleve(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


# ---- Internat ----


class ChambreSchema(Schema):
    id = fields.UUID(dump_only=True)
    batiment = fields.String(allow_none=True)
    numero = fields.String(required=True)
    capacite = fields.Integer(load_default=1)
    genre = fields.String(allow_none=True)
    actif = fields.Boolean(load_default=True)


class AffectationSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_chambre = fields.UUID(required=True)
    id_eleve = fields.UUID(required=True)
    id_annee = fields.UUID(allow_none=True)
    date_debut = fields.Date(required=True)
    date_fin = fields.Date(allow_none=True)
    actif = fields.Boolean(load_default=True)
    created_at = fields.DateTime(dump_only=True)


@blp.route("/internat/chambres")
class InternatChambres(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        return jsonify(ChambreSchema(many=True).dump(tenant_query(InternatChambre).all()))

    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(ChambreSchema)
    @blp.response(201, ChambreSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        row = InternatChambre(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/internat/affectations")
class InternatAffectations(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        return jsonify(AffectationSchema(many=True).dump(tenant_query(InternatAffectation).all()))

    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(AffectationSchema)
    @blp.response(201, AffectationSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        get_or_404_tenant(InternatChambre, data["id_chambre"])
        get_or_404_tenant(Eleve, data["id_eleve"])
        row = InternatAffectation(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


# ---- Infirmerie ----


class SoinSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    date_soin = fields.DateTime(dump_only=True)
    motif = fields.String(required=True)
    traitement = fields.String(allow_none=True)
    soigne_par = fields.UUID(dump_only=True, allow_none=True)
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


@blp.route("/infirmiere/soins")
class InfirmiereSoins(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        q = tenant_query(InfirmiereSoin)
        id_eleve = request.args.get("id_eleve")
        if id_eleve:
            q = q.filter(InfirmiereSoin.id_eleve == uuid.UUID(id_eleve))
        return jsonify(SoinSchema(many=True).dump(q.order_by(InfirmiereSoin.date_soin.desc()).all()))

    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(SoinSchema)
    @blp.response(201, SoinSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        get_or_404_tenant(Eleve, data["id_eleve"])
        row = InfirmiereSoin(id=uuid.uuid4(), soigne_par=user.id, **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


# ---- Bibliothèque ----


class LivreSchema(Schema):
    id = fields.UUID(dump_only=True)
    isbn = fields.String(allow_none=True)
    titre = fields.String(required=True)
    auteur = fields.String(allow_none=True)
    categorie = fields.String(allow_none=True)
    exemplaires = fields.Integer(load_default=1)
    disponibles = fields.Integer(load_default=1)
    actif = fields.Boolean(load_default=True)
    created_at = fields.DateTime(dump_only=True)


class PretSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_livre = fields.UUID(required=True)
    id_eleve = fields.UUID(required=True)
    date_pret = fields.Date(required=True)
    date_retour_prevue = fields.Date(allow_none=True)
    date_retour_effective = fields.Date(allow_none=True)
    statut = fields.String(load_default="en_cours")
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


@blp.route("/bibliotheque/livres")
class BibliothequeLivres(MethodView):
    @jwt_required()
    @require_role(*_STAFF, "enseignant")
    def get(self):
        return jsonify(LivreSchema(many=True).dump(tenant_query(BibliothequeLivre).all()))

    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(LivreSchema)
    @blp.response(201, LivreSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        if "disponibles" not in data and "exemplaires" in data:
            data["disponibles"] = data["exemplaires"]
        row = BibliothequeLivre(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/bibliotheque/prets")
class BibliothequePrets(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        return jsonify(PretSchema(many=True).dump(tenant_query(BibliothequePret).all()))

    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(PretSchema)
    @blp.response(201, PretSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        get_or_404_tenant(Eleve, data["id_eleve"])
        livre = get_or_404_tenant(BibliothequeLivre, data["id_livre"])
        if livre.disponibles <= 0:
            return jsonify({"message": "Aucun exemplaire disponible"}), 409
        livre.disponibles -= 1
        row = BibliothequePret(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/bibliotheque/prets/<uuid:id_pret>/retour")
class BibliothequeRetour(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def post(self, id_pret):
        db = get_db()
        pret = get_or_404_tenant(BibliothequePret, id_pret)
        if pret.statut != "en_cours":
            return jsonify({"message": "Prêt déjà clos"}), 400
        pret.statut = "rendu"
        pret.date_retour_effective = date.today()
        livre = get_or_404_tenant(BibliothequeLivre, pret.id_livre)
        livre.disponibles = min(livre.exemplaires, livre.disponibles + 1)
        db.commit()
        return jsonify(PretSchema().dump(pret))
