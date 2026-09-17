"""Vie scolaire — cantine, transport, internat, infirmière, bibliothèque."""
from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import Decimal

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
    TransportPointage,
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
    id_paiement = fields.UUID(allow_none=True)
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


class CantineMarquageSchema(Schema):
    date = fields.Date(required=True)
    repas = fields.String(load_default="midi")
    eleves = fields.List(fields.Dict(), required=True)


@blp.route("/cantine/presences/marquer")
class CantinePresencesMarquer(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def post(self):
        """Pointage présence cantine pour une date (liste d'élèves)."""
        reject_client_school_id(request.get_json(silent=True))
        body = request.get_json(silent=True) or {}
        date_p = body.get("date")
        if not date_p:
            return jsonify({"message": "date requise"}), 400
        if isinstance(date_p, str):
            date_p = date.fromisoformat(date_p)
        repas = body.get("repas") or "midi"
        eleves = body.get("eleves") or []
        if not isinstance(eleves, list) or not eleves:
            return jsonify({"message": "eleves[] requis"}), 400

        db = get_db()
        created = []
        updated = []
        for item in eleves:
            id_eleve = item.get("id_eleve") if isinstance(item, dict) else item
            present = True if not isinstance(item, dict) else bool(item.get("present", True))
            if not id_eleve:
                continue
            eid = uuid.UUID(str(id_eleve))
            get_or_404_tenant(Eleve, eid)
            existing = (
                tenant_query(CantinePresence)
                .filter(
                    CantinePresence.id_eleve == eid,
                    CantinePresence.date_presence == date_p,
                    CantinePresence.repas == repas,
                )
                .first()
            )
            if existing:
                existing.present = present
                updated.append(existing)
            else:
                row = CantinePresence(
                    id=uuid.uuid4(),
                    id_eleve=eid,
                    date_presence=date_p,
                    repas=repas,
                    present=present,
                )
                apply_tenant_school(row)
                db.add(row)
                created.append(row)
        db.commit()
        return jsonify({
            "date": date_p.isoformat(),
            "repas": repas,
            "crees": len(created),
            "mis_a_jour": len(updated),
            "presences": CantinePresenceSchema(many=True).dump(created + updated),
        }), 201


@blp.route("/cantine/facturation")
class CantineFacturation(MethodView):
    @jwt_required()
    @require_role(*_STAFF, "agent_comptable")
    def get(self):
        """Résumé mensuel cantine : présences × abonnements, lien paiement optionnel."""
        annee = request.args.get("annee", type=int)
        mois = request.args.get("mois", type=int)
        if not annee or not mois or mois < 1 or mois > 12:
            return jsonify({"message": "annee et mois requis (1-12)"}), 400

        id_paiement = request.args.get("id_paiement")
        premier = date(annee, mois, 1)
        dernier = date(annee, mois, calendar.monthrange(annee, mois)[1])

        abonnements = (
            tenant_query(CantineAbonnement)
            .filter(
                CantineAbonnement.actif.is_(True),
                CantineAbonnement.date_debut <= dernier,
            )
            .all()
        )
        abonnements = [
            a
            for a in abonnements
            if a.date_fin is None or a.date_fin >= premier
        ]

        presences = (
            tenant_query(CantinePresence)
            .filter(
                CantinePresence.date_presence >= premier,
                CantinePresence.date_presence <= dernier,
                CantinePresence.present.is_(True),
            )
            .all()
        )
        present_count: dict[uuid.UUID, int] = {}
        for p in presences:
            present_count[p.id_eleve] = present_count.get(p.id_eleve, 0) + 1

        lignes = []
        total = Decimal(0)
        for abo in abonnements:
            n_jours = present_count.get(abo.id_eleve, 0)
            montant_abo = Decimal(str(abo.montant or 0))
            # Facturation forfaitaire mensuelle si montant ; sinon 0 (présences informatives)
            montant_du = montant_abo
            total += montant_du
            lignes.append({
                "id_abonnement": str(abo.id),
                "id_eleve": str(abo.id_eleve),
                "formule": abo.formule,
                "jours_presents": n_jours,
                "montant": float(montant_du),
                "id_paiement": str(abo.id_paiement) if abo.id_paiement else None,
            })

        # Lien optionnel paiement → abonnements du mois sans paiement
        linked = 0
        if id_paiement:
            db = get_db()
            pid = uuid.UUID(id_paiement)
            for abo in abonnements:
                if abo.id_paiement is None:
                    abo.id_paiement = pid
                    linked += 1
            db.commit()
            for ligne in lignes:
                if ligne["id_paiement"] is None:
                    ligne["id_paiement"] = str(pid)

        return jsonify({
            "annee": annee,
            "mois": mois,
            "lignes": lignes,
            "total": float(total),
            "nb_abonnements": len(lignes),
            "jours_presents_total": sum(present_count.values()),
            "paiements_lies": linked,
        })


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


class TransportPointageSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_arret = fields.UUID(required=True)
    id_eleve = fields.UUID(dump_only=True)
    date_pointage = fields.Date(dump_only=True)
    embarque = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


@blp.route("/transport/pointage")
class TransportPointageResource(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        q = tenant_query(TransportPointage)
        date_p = request.args.get("date")
        id_arret = request.args.get("id_arret")
        if date_p:
            q = q.filter(TransportPointage.date_pointage == date_p)
        if id_arret:
            q = q.filter(TransportPointage.id_arret == uuid.UUID(id_arret))
        return jsonify(TransportPointageSchema(many=True).dump(q.all()))

    @jwt_required()
    @require_role(*_STAFF)
    def post(self):
        """Embarquement : date + arrêt + liste d'élèves."""
        reject_client_school_id(request.get_json(silent=True))
        body = request.get_json(silent=True) or {}
        date_p = body.get("date")
        id_arret = body.get("id_arret")
        eleves = body.get("eleves") or body.get("eleve_ids") or []
        if not date_p or not id_arret:
            return jsonify({"message": "date et id_arret requis"}), 400
        if isinstance(date_p, str):
            date_p = date.fromisoformat(date_p)
        if not isinstance(eleves, list) or not eleves:
            return jsonify({"message": "eleves[] requis"}), 400

        db = get_db()
        arret = get_or_404_tenant(TransportArret, uuid.UUID(str(id_arret)))
        created = []
        for raw in eleves:
            eid = uuid.UUID(str(raw.get("id_eleve") if isinstance(raw, dict) else raw))
            get_or_404_tenant(Eleve, eid)
            existing = (
                tenant_query(TransportPointage)
                .filter(
                    TransportPointage.id_arret == arret.id,
                    TransportPointage.date_pointage == date_p,
                    TransportPointage.id_eleve == eid,
                )
                .first()
            )
            if existing:
                existing.embarque = True
                created.append(existing)
                continue
            row = TransportPointage(
                id=uuid.uuid4(),
                id_arret=arret.id,
                id_eleve=eid,
                date_pointage=date_p,
                embarque=True,
            )
            apply_tenant_school(row)
            db.add(row)
            created.append(row)
        db.commit()
        return jsonify({
            "date": date_p.isoformat(),
            "id_arret": str(arret.id),
            "nb": len(created),
            "pointages": TransportPointageSchema(many=True).dump(created),
        }), 201


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
    amende = fields.Decimal(as_string=True, load_default="0")
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


@blp.route("/bibliotheque/prets/retards")
class BibliothequePretsRetards(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    def get(self):
        """Prêts en retard (date_retour_prevue < aujourd'hui, non rendus)."""
        today = date.today()
        rows = (
            tenant_query(BibliothequePret)
            .filter(
                BibliothequePret.statut == "en_cours",
                BibliothequePret.date_retour_prevue.isnot(None),
                BibliothequePret.date_retour_prevue < today,
            )
            .order_by(BibliothequePret.date_retour_prevue.asc())
            .all()
        )
        payload = []
        for pret in rows:
            jours = (today - pret.date_retour_prevue).days if pret.date_retour_prevue else 0
            item = PretSchema().dump(pret)
            item["jours_retard"] = jours
            payload.append(item)
        return jsonify({"retards": payload, "nb": len(payload), "au": today.isoformat()})


@blp.route("/bibliotheque/prets/<uuid:id_pret>")
class BibliothequePretDetail(MethodView):
    @jwt_required()
    @require_role(*_STAFF)
    @blp.arguments(PretSchema(partial=True))
    def patch(self, data, id_pret):
        """Mise à jour partielle (ex. amende)."""
        db = get_db()
        pret = get_or_404_tenant(BibliothequePret, id_pret)
        for k, v in data.items():
            if k in ("id_livre", "id_eleve"):
                continue
            setattr(pret, k, v)
        db.commit()
        return jsonify(PretSchema().dump(pret))


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
        body = request.get_json(silent=True) or {}
        if "amende" in body and body["amende"] is not None:
            pret.amende = Decimal(str(body["amende"]))
        livre = get_or_404_tenant(BibliothequeLivre, pret.id_livre)
        livre.disponibles = min(livre.exemplaires, livre.disponibles + 1)
        db.commit()
        return jsonify(PretSchema().dump(pret))
