"""Comptabilité SYSCOHADA — écritures, états, paie."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import EcritureComptable, PaieLigne, PaiePeriode
from app.services.tenant import (
    apply_tenant_school,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)

blp = Blueprint("comptabilite", __name__, description="Comptabilité et paie")

_COMPTA = ("administrateur", "directeur", "agent_comptable")


class EcritureSchema(Schema):
    id = fields.UUID(dump_only=True)
    date_ecriture = fields.Date(required=True)
    libelle = fields.String(required=True)
    compte_debit = fields.String(required=True)
    compte_credit = fields.String(required=True)
    montant = fields.Decimal(as_string=True, required=True)
    reference = fields.String(allow_none=True)
    id_paiement = fields.UUID(allow_none=True)
    journal = fields.String(allow_none=True)
    piece_url = fields.String(allow_none=True)
    saisi_par = fields.UUID(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class PaiePeriodeSchema(Schema):
    id = fields.UUID(dump_only=True)
    libelle = fields.String(required=True)
    date_debut = fields.Date(required=True)
    date_fin = fields.Date(required=True)
    statut = fields.String(load_default="ouverte")
    cloture_le = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class PaieLigneSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_periode = fields.UUID(required=True)
    id_utilisateur = fields.UUID(allow_none=True)
    id_enseignant = fields.UUID(allow_none=True)
    matricule = fields.String(allow_none=True)
    brut = fields.Decimal(as_string=True, load_default="0")
    retenues = fields.Decimal(as_string=True, load_default="0")
    net = fields.Decimal(as_string=True, load_default="0")
    details = fields.Dict(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


@blp.route("/ecritures")
class EcrituresResource(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def get(self):
        q = tenant_query(EcritureComptable)
        date_debut = request.args.get("date_debut")
        date_fin = request.args.get("date_fin")
        if date_debut:
            q = q.filter(EcritureComptable.date_ecriture >= date_debut)
        if date_fin:
            q = q.filter(EcritureComptable.date_ecriture <= date_fin)
        rows = q.order_by(EcritureComptable.date_ecriture.desc()).limit(500).all()
        return jsonify(EcritureSchema(many=True).dump(rows))

    @jwt_required()
    @require_role(*_COMPTA)
    @blp.arguments(EcritureSchema)
    @blp.response(201, EcritureSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        row = EcritureComptable(id=uuid.uuid4(), saisi_par=user.id, **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/ecritures/<uuid:id_ecriture>")
class EcritureDetail(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def get(self, id_ecriture):
        return jsonify(EcritureSchema().dump(get_or_404_tenant(EcritureComptable, id_ecriture)))

    @jwt_required()
    @require_role(*_COMPTA)
    @blp.arguments(EcritureSchema(partial=True))
    def put(self, data, id_ecriture):
        db = get_db()
        row = get_or_404_tenant(EcritureComptable, id_ecriture)
        for k, v in data.items():
            setattr(row, k, v)
        db.commit()
        return jsonify(EcritureSchema().dump(row))

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_ecriture):
        db = get_db()
        row = get_or_404_tenant(EcritureComptable, id_ecriture)
        db.delete(row)
        db.commit()
        return jsonify({"message": "Écriture supprimée"})


@blp.route("/etats/balance")
class EtatBalance(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def get(self):
        """Balance simple débit/crédit par compte."""
        rows = tenant_query(EcritureComptable).all()
        comptes: dict[str, dict] = defaultdict(lambda: {"debit": Decimal(0), "credit": Decimal(0)})
        for e in rows:
            comptes[e.compte_debit]["debit"] += Decimal(e.montant)
            comptes[e.compte_credit]["credit"] += Decimal(e.montant)
        balance = [
            {
                "compte": compte,
                "debit": float(v["debit"]),
                "credit": float(v["credit"]),
                "solde": float(v["debit"] - v["credit"]),
            }
            for compte, v in sorted(comptes.items())
        ]
        return jsonify({"balance": balance})


@blp.route("/etats/bilan")
class EtatBilan(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def get(self):
        """Bilan très simplifié : classes 1–5 actif/passif, 6–7 charges/produits."""
        rows = tenant_query(EcritureComptable).all()
        actif = Decimal(0)
        passif = Decimal(0)
        charges = Decimal(0)
        produits = Decimal(0)
        for e in rows:
            m = Decimal(e.montant)
            for compte, sens in ((e.compte_debit, "D"), (e.compte_credit, "C")):
                classe = (compte or "0")[:1]
                if classe in ("2", "3", "4", "5"):
                    if sens == "D":
                        actif += m
                    else:
                        actif -= m
                elif classe == "1":
                    if sens == "C":
                        passif += m
                    else:
                        passif -= m
                elif classe == "6":
                    if sens == "D":
                        charges += m
                    else:
                        charges -= m
                elif classe == "7":
                    if sens == "C":
                        produits += m
                    else:
                        produits -= m
        resultat = produits - charges
        return jsonify({
            "actif": float(actif),
            "passif": float(passif),
            "charges": float(charges),
            "produits": float(produits),
            "resultat": float(resultat),
        })


@blp.route("/paie/periodes")
class PaiePeriodesResource(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def get(self):
        rows = tenant_query(PaiePeriode).order_by(PaiePeriode.date_debut.desc()).all()
        return jsonify(PaiePeriodeSchema(many=True).dump(rows))

    @jwt_required()
    @require_role(*_COMPTA)
    @blp.arguments(PaiePeriodeSchema)
    @blp.response(201, PaiePeriodeSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        row = PaiePeriode(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/paie/periodes/<uuid:id_periode>/cloturer")
class PaiePeriodeCloture(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def post(self, id_periode):
        db = get_db()
        row = get_or_404_tenant(PaiePeriode, id_periode)
        row.statut = "cloturee"
        row.cloture_le = datetime.now(UTC)
        db.commit()
        return jsonify(PaiePeriodeSchema().dump(row))


@blp.route("/paie/lignes")
class PaieLignesResource(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def get(self):
        q = tenant_query(PaieLigne)
        id_periode = request.args.get("id_periode")
        if id_periode:
            q = q.filter(PaieLigne.id_periode == uuid.UUID(id_periode))
        return jsonify(PaieLigneSchema(many=True).dump(q.all()))

    @jwt_required()
    @require_role(*_COMPTA)
    @blp.arguments(PaieLigneSchema)
    @blp.response(201, PaieLigneSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        get_or_404_tenant(PaiePeriode, data["id_periode"])
        brut = Decimal(str(data.get("brut") or 0))
        retenues = Decimal(str(data.get("retenues") or 0))
        if "net" not in data or data.get("net") is None:
            data["net"] = brut - retenues
        row = PaieLigne(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201
