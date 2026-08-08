"""Module 3 — Routes finance : frais, échéances, paiements."""
import uuid
from decimal import Decimal

from flask import jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from sqlalchemy import func, text

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import get_parent_eleve_ids, parent_has_eleve_access, require_role
from app.extensions import get_db
from app.models import EcheancePaiement, FraisScolaire, Inscription, NiveauEtude, Paiement, AnneeScolaire, Eleve
from app.schemas.finance import (
    AnnulationPaiementSchema,
    EcheancePaiementSchema,
    FraisScolaireSchema,
    PaiementCreateSchema,
    PaiementSchema,
)
from app.services.generation_recu import generer_recu_pdf
from app.services.finance_arrieres import list_arrieres
from app.services.relance_arrieres import relancer_arrieres
from app.utils.audit_logger import log_audit

blp = Blueprint("finance", __name__, url_prefix="/finance", description="Finance et comptabilité")


def _serialize_frais(db, frais):
    data = FraisScolaireSchema().dump(frais)
    niveau = db.query(NiveauEtude).filter(NiveauEtude.id == frais.id_niveau).first()
    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == frais.id_annee).first()
    echeances = (
        db.query(EcheancePaiement)
        .filter(EcheancePaiement.id_frais == frais.id)
        .order_by(EcheancePaiement.date_echeance)
        .all()
    )
    data["niveau_libelle"] = niveau.libelle if niveau else None
    data["annee_libelle"] = annee.libelle if annee else None
    data["echeances"] = EcheancePaiementSchema(many=True).dump(echeances)
    data["montant_total"] = float(frais.montant_total)
    return data


def _serialize_paiement(db, paiement):
    data = PaiementSchema().dump(paiement)
    eleve = db.query(Eleve).filter(Eleve.id == paiement.id_eleve).first()
    data["montant_verse"] = float(paiement.montant_verse)
    if eleve:
        data["eleve_nom"] = f"{eleve.prenom} {eleve.nom}"
        data["matricule"] = eleve.matricule
    return data


@blp.route("/frais")
class FraisResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable", "secretariat")
    def get(self):
        db = get_db()
        q = db.query(FraisScolaire)
        id_annee = request.args.get("id_annee")
        if id_annee:
            q = q.filter(FraisScolaire.id_annee == uuid.UUID(id_annee))
        frais_list = q.all()
        return jsonify([_serialize_frais(db, f) for f in frais_list])

    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(FraisScolaireSchema)
    @blp.response(201, FraisScolaireSchema)
    def post(self, data):
        db = get_db()
        frais = FraisScolaire(id=uuid.uuid4(), **data)
        db.add(frais)
        db.commit()
        return frais, 201


@blp.route("/echeances")
class EcheancesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable", "secretariat")
    @blp.response(200, EcheancePaiementSchema(many=True))
    def get(self):
        db = get_db()
        id_frais = request.args.get("id_frais")
        q = db.query(EcheancePaiement)
        if id_frais:
            q = q.filter(EcheancePaiement.id_frais == uuid.UUID(id_frais))
        return q.all()

    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(EcheancePaiementSchema)
    @blp.response(201, EcheancePaiementSchema)
    def post(self, data):
        db = get_db()
        echeance = EcheancePaiement(id=uuid.uuid4(), **data)
        db.add(echeance)
        db.commit()
        return echeance, 201


@blp.route("/paiements")
class PaiementsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable", "secretariat", "parent")
    def get(self):
        db = get_db()
        user = get_current_user()
        q = db.query(Paiement)
        id_eleve = request.args.get("id_eleve")
        id_annee = request.args.get("id_annee")
        if user.role == "parent":
            eleve_ids = get_parent_eleve_ids(user)
            if not eleve_ids:
                return jsonify([])
            q = q.filter(Paiement.id_eleve.in_(eleve_ids))
        if id_eleve:
            eid = uuid.UUID(id_eleve)
            if user.role == "parent" and not parent_has_eleve_access(user, eid):
                return jsonify({"message": "Accès refusé"}), 403
            q = q.filter(Paiement.id_eleve == eid)
        if id_annee:
            q = q.filter(Paiement.id_annee == uuid.UUID(id_annee))
        paiements = q.order_by(Paiement.date_paiement.desc()).all()
        return jsonify([_serialize_paiement(db, p) for p in paiements])

    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(PaiementCreateSchema)
    @blp.response(201, PaiementSchema)
    def post(self, data):
        db = get_db()
        user = get_current_user()

        # Générer numéro de reçu via séquence PostgreSQL
        numero_recu = db.execute(text("SELECT 'REC-' || nextval('seq_numero_recu')")).scalar()

        paiement = Paiement(
            id=uuid.uuid4(),
            numero_recu=numero_recu,
            encaisse_par=user.id,
            **data,
        )
        db.add(paiement)
        db.commit()
        log_audit("PAIEMENT_ENCAISSE", user.id, "paiement", paiement.id, {"montant": str(data["montant_verse"])})
        return paiement, 201


@blp.route("/paiements/<uuid:id_paiement>/annuler")
class AnnulerPaiement(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(AnnulationPaiementSchema)
    def post(self, data, id_paiement):
        db = get_db()
        user = get_current_user()
        paiement = db.query(Paiement).filter(Paiement.id == id_paiement).first()
        if not paiement:
            return jsonify({"message": "Paiement introuvable"}), 404
        if paiement.annule:
            return jsonify({"message": "Paiement déjà annulé"}), 400
        # Jamais de DELETE — annulation traçable uniquement
        paiement.annule = True
        paiement.motif_annulation = data["motif_annulation"]
        db.commit()
        log_audit("PAIEMENT_ANNULE", user.id, "paiement", paiement.id, {"motif": data["motif_annulation"]})
        return PaiementSchema().dump(paiement)


@blp.route("/paiements/<uuid:id_paiement>/recu")
class RecuPaiement(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable", "secretariat", "parent")
    def get(self, id_paiement):
        db = get_db()
        user = get_current_user()
        paiement = db.query(Paiement).filter(Paiement.id == id_paiement).first()
        if not paiement:
            return jsonify({"message": "Paiement introuvable"}), 404
        if user.role == "parent" and not parent_has_eleve_access(user, paiement.id_eleve):
            return jsonify({"message": "Accès refusé"}), 403
        try:
            path = generer_recu_pdf(id_paiement)
            return send_file(
                path,
                mimetype="application/pdf",
                as_attachment=False,
                download_name=f"{paiement.numero_recu}.pdf",
            )
        except ValueError as e:
            return jsonify({"message": str(e)}), 400


@blp.route("/arrieres")
class ArrieresResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable", "secretariat")
    def get(self):
        """Calcule les arriérés par élève : Σ(échéances dues) − Σ(paiements non annulés)."""
        db = get_db()
        id_annee = request.args.get("id_annee")
        if not id_annee:
            return jsonify({"message": "id_annee requis"}), 400

        id_classe = request.args.get("id_classe")
        classe_uuid = uuid.UUID(id_classe) if id_classe else None
        arrieres = list_arrieres(db, uuid.UUID(id_annee), id_classe=classe_uuid)
        return jsonify([
            {**a, "id_eleve": str(a["id_eleve"])} for a in arrieres
        ])


@blp.route("/arrieres/relancer")
class ArrieresRelancer(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    def post(self):
        db = get_db()
        user = get_current_user()
        data = request.json or {}
        id_annee = data.get("id_annee") or request.args.get("id_annee")
        if not id_annee:
            return jsonify({"message": "id_annee requis"}), 400
        canal = data.get("canal", "email")
        if canal not in ("email", "sms"):
            return jsonify({"message": "canal invalide (email ou sms)"}), 400
        auto_envoyer = bool(data.get("auto_envoyer", True))
        result = relancer_arrieres(
            db,
            uuid.UUID(id_annee),
            canal=canal,
            auto_envoyer=auto_envoyer,
        )
        log_audit(
            "RELANCE_ARRIERES",
            user.id,
            details={"id_annee": str(id_annee), **result},
        )
        return jsonify({
            "message": f"{result['notifications_crees']} relance(s) créée(s)",
            **result,
        })


@blp.route("/arrieres/export")
class ArrieresExport(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable", "secretariat")
    def get(self):
        from io import BytesIO

        from openpyxl import Workbook

        id_annee = request.args.get("id_annee")
        if not id_annee:
            return jsonify({"message": "id_annee requis"}), 400

        db = get_db()
        rows = db.execute(
            text("""
                SELECT e.matricule, e.nom, e.prenom,
                       COALESCE(SUM(ec.montant), 0) AS total_du,
                       COALESCE((
                           SELECT SUM(p.montant_verse)
                           FROM paiement p
                           WHERE p.id_eleve = i.id_eleve AND p.id_annee = :id_annee AND p.annule = false
                       ), 0) AS total_paye
                FROM inscription i
                JOIN eleve e ON e.id = i.id_eleve
                JOIN classe c ON c.id = i.id_classe
                JOIN frais_scolaire fs ON fs.id_niveau = c.id_niveau AND fs.id_annee = i.id_annee
                JOIN echeance_paiement ec ON ec.id_frais = fs.id
                WHERE i.id_annee = :id_annee AND i.statut IN ('inscrit', 'reinscrit')
                GROUP BY i.id_eleve, e.matricule, e.nom, e.prenom
            """),
            {"id_annee": id_annee},
        ).fetchall()

        wb = Workbook()
        ws = wb.active
        ws.title = "Arriérés"
        ws.append(["Matricule", "Nom", "Prénom", "Total dû", "Total payé", "Arriéré"])
        for r in rows:
            arriere = float(r[3]) - float(r[4])
            if arriere > 0:
                ws.append([r[0], r[1], r[2], float(r[3]), float(r[4]), round(arriere, 2)])

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="arrieres.xlsx",
        )
