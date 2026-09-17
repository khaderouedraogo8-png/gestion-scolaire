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


def _filtered_ecritures():
    q = tenant_query(EcritureComptable)
    d_from = request.args.get("from") or request.args.get("date_debut")
    d_to = request.args.get("to") or request.args.get("date_fin")
    if d_from:
        q = q.filter(EcritureComptable.date_ecriture >= d_from)
    if d_to:
        q = q.filter(EcritureComptable.date_ecriture <= d_to)
    return q


def _aggregats_comptes(rows: list[EcritureComptable]) -> dict[str, dict]:
    comptes: dict[str, dict] = defaultdict(
        lambda: {"debit": Decimal(0), "credit": Decimal(0), "mouvements": 0}
    )
    for e in rows:
        m = Decimal(e.montant)
        comptes[e.compte_debit]["debit"] += m
        comptes[e.compte_debit]["mouvements"] += 1
        comptes[e.compte_credit]["credit"] += m
        comptes[e.compte_credit]["mouvements"] += 1
    return comptes


@blp.route("/ecritures")
class EcrituresResource(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def get(self):
        q = _filtered_ecritures()
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


@blp.route("/grand-livre")
class GrandLivre(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def get(self):
        """Grand livre filtré : ?compte=&from=&to=."""
        compte = (request.args.get("compte") or "").strip()
        q = _filtered_ecritures()
        if compte:
            q = q.filter(
                (EcritureComptable.compte_debit == compte)
                | (EcritureComptable.compte_credit == compte)
            )
        rows = q.order_by(
            EcritureComptable.date_ecriture.asc(), EcritureComptable.created_at.asc()
        ).all()

        lignes = []
        solde = Decimal(0)
        total_debit = Decimal(0)
        total_credit = Decimal(0)
        for e in rows:
            m = Decimal(e.montant)
            debit = m if (not compte or e.compte_debit == compte) else Decimal(0)
            credit = m if (not compte or e.compte_credit == compte) else Decimal(0)
            if compte:
                solde += debit - credit
            total_debit += debit
            total_credit += credit
            lignes.append({
                "id": str(e.id),
                "date_ecriture": e.date_ecriture.isoformat() if e.date_ecriture else None,
                "libelle": e.libelle,
                "compte_debit": e.compte_debit,
                "compte_credit": e.compte_credit,
                "debit": float(debit),
                "credit": float(credit),
                "solde": float(solde) if compte else None,
                "reference": e.reference,
                "journal": e.journal,
                "montant": float(m),
            })

        return jsonify({
            "compte": compte or None,
            "from": request.args.get("from") or request.args.get("date_debut"),
            "to": request.args.get("to") or request.args.get("date_fin"),
            "lignes": lignes,
            "total_debit": float(total_debit),
            "total_credit": float(total_credit),
            "solde": float(solde) if compte else float(total_debit - total_credit),
            "nb_lignes": len(lignes),
        })


@blp.route("/etats/balance")
class EtatBalance(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def get(self):
        """Balance simple débit/crédit par compte."""
        rows = _filtered_ecritures().all()
        comptes = _aggregats_comptes(rows)
        balance = [
            {
                "compte": compte,
                "debit": float(v["debit"]),
                "credit": float(v["credit"]),
                "solde": float(v["debit"] - v["credit"]),
                "mouvements": v["mouvements"],
            }
            for compte, v in sorted(comptes.items())
        ]
        return jsonify({
            "balance": balance,
            "from": request.args.get("from") or request.args.get("date_debut"),
            "to": request.args.get("to") or request.args.get("date_fin"),
        })


@blp.route("/etats/bilan")
class EtatBilan(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def get(self):
        """Bilan simplifié SYSCOHADA avec détail par compte."""
        rows = _filtered_ecritures().all()
        comptes = _aggregats_comptes(rows)

        actif_detail = []
        passif_detail = []
        actif = Decimal(0)
        passif = Decimal(0)

        for compte, v in sorted(comptes.items()):
            solde = v["debit"] - v["credit"]
            classe = (compte or "0")[:1]
            item = {
                "compte": compte,
                "debit": float(v["debit"]),
                "credit": float(v["credit"]),
                "solde": float(solde),
            }
            if classe in ("2", "3", "5") or (classe == "4" and solde >= 0):
                actif += solde
                actif_detail.append(item)
            elif classe == "1" or (classe == "4" and solde < 0):
                passif += -solde if solde < 0 else solde
                passif_detail.append({**item, "solde": float(-solde if solde < 0 else solde)})

        charges = Decimal(0)
        produits = Decimal(0)
        for e in rows:
            m = Decimal(e.montant)
            if (e.compte_debit or "")[:1] == "6":
                charges += m
            if (e.compte_credit or "")[:1] == "6":
                charges -= m
            if (e.compte_credit or "")[:1] == "7":
                produits += m
            if (e.compte_debit or "")[:1] == "7":
                produits -= m

        resultat = produits - charges
        if resultat >= 0:
            passif += resultat
            passif_detail.append({
                "compte": "130",
                "libelle": "Résultat de l'exercice",
                "debit": 0.0,
                "credit": float(resultat),
                "solde": float(resultat),
            })
        else:
            actif += abs(resultat)
            actif_detail.append({
                "compte": "130",
                "libelle": "Perte de l'exercice",
                "debit": float(abs(resultat)),
                "credit": 0.0,
                "solde": float(abs(resultat)),
            })

        return jsonify({
            "actif": float(actif),
            "passif": float(passif),
            "charges": float(charges),
            "produits": float(produits),
            "resultat": float(resultat),
            "actif_detail": actif_detail,
            "passif_detail": passif_detail,
            "equilibre": abs(float(actif) - float(passif)) < 0.02,
            "from": request.args.get("from") or request.args.get("date_debut"),
            "to": request.args.get("to") or request.args.get("date_fin"),
        })


@blp.route("/etats/compte-resultat")
class EtatCompteResultat(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def get(self):
        """Compte de résultat : charges (6) / produits (7)."""
        rows = _filtered_ecritures().all()
        charges_map: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
        produits_map: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
        for e in rows:
            m = Decimal(e.montant)
            if (e.compte_debit or "")[:1] == "6":
                charges_map[e.compte_debit] += m
            if (e.compte_credit or "")[:1] == "6":
                charges_map[e.compte_credit] -= m
            if (e.compte_credit or "")[:1] == "7":
                produits_map[e.compte_credit] += m
            if (e.compte_debit or "")[:1] == "7":
                produits_map[e.compte_debit] -= m

        total_charges = sum(charges_map.values(), Decimal(0))
        total_produits = sum(produits_map.values(), Decimal(0))
        return jsonify({
            "charges": [
                {"compte": c, "montant": float(v)}
                for c, v in sorted(charges_map.items())
                if v != 0
            ],
            "produits": [
                {"compte": c, "montant": float(v)}
                for c, v in sorted(produits_map.items())
                if v != 0
            ],
            "total_charges": float(total_charges),
            "total_produits": float(total_produits),
            "resultat": float(total_produits - total_charges),
            "from": request.args.get("from") or request.args.get("date_debut"),
            "to": request.args.get("to") or request.args.get("date_fin"),
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


class PaieCalculSchema(Schema):
    taux_retenue = fields.Float(allow_none=True)
    heures = fields.Dict(keys=fields.String(), values=fields.Float(), load_default=dict)


@blp.route("/paie/periodes/<uuid:id_periode>/calculer")
class PaiePeriodeCalculer(MethodView):
    @jwt_required()
    @require_role(*_COMPTA)
    def post(self, id_periode):
        """Calcule brut/retenues/net pour enseignants actifs + écritures SYSCOHADA."""
        from app.services.paie_calcul import calculer_paie_periode

        db = get_db()
        user = get_current_user()
        periode = get_or_404_tenant(PaiePeriode, id_periode)
        if periode.statut == "cloturee":
            return jsonify({"message": "Période clôturée"}), 400

        body = request.get_json(silent=True) or {}
        reject_client_school_id(body)
        taux = body.get("taux_retenue")
        heures = body.get("heures") or {}

        result = calculer_paie_periode(
            db,
            periode,
            taux_retenue=float(taux) if taux is not None else None,
            heures_map={str(k): float(v) for k, v in heures.items()},
            saisi_par=user.id,
        )
        return jsonify({
            "periode": PaiePeriodeSchema().dump(result["periode"]),
            "lignes": PaieLigneSchema(many=True).dump(result["lignes"]),
            "totaux": result["totaux"],
            "taux_retenue": result["taux_retenue"],
            "ecritures": result["ecritures"],
        })


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
