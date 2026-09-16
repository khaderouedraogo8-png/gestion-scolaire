"""Module 3 — Routes finance : frais, échéances, paiements."""
import uuid

from flask import abort, jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from sqlalchemy import text

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import (
    get_parent_eleve_ids,
    parent_has_eleve_access,
    require_role,
)
from app.extensions import get_db
from app.models import (
    AnneeScolaire,
    Classe,
    EcheancePaiement,
    Eleve,
    FraisScolaire,
    NiveauEtude,
    Paiement,
)
from app.schemas.finance import (
    AnnulationPaiementSchema,
    EcheancePaiementSchema,
    FraisScolaireSchema,
    PaiementCreateSchema,
    PaiementSchema,
    RelanceArrieresSchema,
)
from app.services.finance_arrieres import list_arrieres
from app.services.generation_recu import generer_recu_pdf
from app.services.relance_arrieres import relancer_arrieres
from app.services.tenant import (
    apply_tenant_school,
    assert_same_school,
    get_current_school_id,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)
from app.utils.audit_logger import log_audit
from app.utils.pagination import empty_pagination, paginate_query, pagination_payload, parse_pagination

blp = Blueprint("finance", __name__, url_prefix="/finance", description="Finance et comptabilité")


def _tenant_echeance_query(db):
    """Échéances isolées via FraisScolaire.school_id (parent-only)."""
    return (
        db.query(EcheancePaiement)
        .join(FraisScolaire, EcheancePaiement.id_frais == FraisScolaire.id)
        .filter(FraisScolaire.school_id == get_current_school_id())
    )


def _serialize_frais(db, frais):
    data = FraisScolaireSchema().dump(frais)
    niveau = tenant_query(NiveauEtude).filter(NiveauEtude.id == frais.id_niveau).first()
    annee = tenant_query(AnneeScolaire).filter(AnneeScolaire.id == frais.id_annee).first()
    echeances = (
        _tenant_echeance_query(db)
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
    eleve = tenant_query(Eleve).filter(Eleve.id == paiement.id_eleve).first()
    data["montant_verse"] = float(paiement.montant_verse)
    if eleve:
        data["eleve_nom"] = f"{eleve.prenom} {eleve.nom}"
        data["matricule"] = eleve.matricule
    return data


@blp.route("/frais")
class FraisResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    def get(self):
        db = get_db()
        q = tenant_query(FraisScolaire)
        id_annee = request.args.get("id_annee")
        if id_annee:
            get_or_404_tenant(AnneeScolaire, id_annee)
            q = q.filter(FraisScolaire.id_annee == uuid.UUID(id_annee))
        frais_list = q.all()
        return jsonify([_serialize_frais(db, f) for f in frais_list])

    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(FraisScolaireSchema)
    @blp.response(201, FraisScolaireSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        niveau = get_or_404_tenant(NiveauEtude, data["id_niveau"])
        annee = get_or_404_tenant(AnneeScolaire, data["id_annee"])
        assert_same_school(niveau, annee)
        frais = FraisScolaire(id=uuid.uuid4(), **data)
        apply_tenant_school(frais)
        db.add(frais)
        db.commit()
        return frais, 201


@blp.route("/echeances")
class EcheancesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.response(200, EcheancePaiementSchema(many=True))
    def get(self):
        db = get_db()
        id_frais = request.args.get("id_frais")
        q = _tenant_echeance_query(db)
        if id_frais:
            get_or_404_tenant(FraisScolaire, id_frais)
            q = q.filter(EcheancePaiement.id_frais == uuid.UUID(id_frais))
        return q.all()

    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(EcheancePaiementSchema)
    @blp.response(201, EcheancePaiementSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        get_or_404_tenant(FraisScolaire, data["id_frais"])
        echeance = EcheancePaiement(id=uuid.uuid4(), **data)
        db.add(echeance)
        db.commit()
        return echeance, 201


@blp.route("/paiements")
class PaiementsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable", "parent")
    def get(self):
        db = get_db()
        user = get_current_user()
        q = tenant_query(Paiement)
        id_eleve = request.args.get("id_eleve")
        id_annee = request.args.get("id_annee")
        if id_annee:
            get_or_404_tenant(AnneeScolaire, id_annee)
        if user.role == "parent":
            eleve_ids = get_parent_eleve_ids(user)
            if not eleve_ids:
                return jsonify(empty_pagination())
            q = q.filter(Paiement.id_eleve.in_(eleve_ids))
        if id_eleve:
            eid = uuid.UUID(id_eleve)
            get_or_404_tenant(Eleve, eid)
            if user.role == "parent" and not parent_has_eleve_access(user, eid):
                return jsonify({"message": "Accès refusé"}), 403
            q = q.filter(Paiement.id_eleve == eid)
        if id_annee:
            q = q.filter(Paiement.id_annee == uuid.UUID(id_annee))
        page, per_page = parse_pagination()
        items, total, pages = paginate_query(
            q.order_by(Paiement.date_paiement.desc()), page, per_page
        )
        return jsonify(
            pagination_payload(
                [_serialize_paiement(db, p) for p in items],
                page=page,
                per_page=per_page,
                total=total,
                pages=pages,
            )
        )

    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(PaiementCreateSchema)
    @blp.response(201, PaiementSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()

        eleve = get_or_404_tenant(Eleve, data["id_eleve"])
        annee = get_or_404_tenant(AnneeScolaire, data["id_annee"])
        assert_same_school(eleve, annee)
        if data.get("id_echeance"):
            echeance = (
                _tenant_echeance_query(db)
                .filter(EcheancePaiement.id == data["id_echeance"])
                .first()
            )
            if echeance is None:
                abort(404)
            frais = get_or_404_tenant(FraisScolaire, echeance.id_frais)
            assert_same_school(eleve, annee, frais)

        # Générer numéro de reçu via séquence PostgreSQL
        numero_recu = db.execute(text("SELECT 'REC-' || nextval('seq_numero_recu')")).scalar()

        paiement = Paiement(
            id=uuid.uuid4(),
            numero_recu=numero_recu,
            encaisse_par=user.id,
            **data,
        )
        apply_tenant_school(paiement)
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
        paiement = get_or_404_tenant(Paiement, id_paiement)
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
    @require_role("administrateur", "directeur", "agent_comptable", "parent")
    def get(self, id_paiement):
        user = get_current_user()
        paiement = get_or_404_tenant(Paiement, id_paiement)
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
    @require_role("administrateur", "directeur", "agent_comptable")
    def get(self):
        """Calcule les arriérés par élève : Σ(échéances dues) − Σ(paiements non annulés)."""
        db = get_db()
        id_annee = request.args.get("id_annee")
        if not id_annee:
            return jsonify({"message": "id_annee requis"}), 400

        get_or_404_tenant(AnneeScolaire, id_annee)
        id_classe = request.args.get("id_classe")
        classe_uuid = uuid.UUID(id_classe) if id_classe else None
        if classe_uuid:
            get_or_404_tenant(Classe, classe_uuid)
        arrieres = list_arrieres(
            db,
            uuid.UUID(id_annee),
            id_classe=classe_uuid,
            school_id=get_current_school_id(),
        )
        return jsonify([
            {**a, "id_eleve": str(a["id_eleve"])} for a in arrieres
        ])


@blp.route("/arrieres/relancer")
class ArrieresRelancer(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(RelanceArrieresSchema)
    def post(self, data):
        db = get_db()
        user = get_current_user()
        id_annee = data["id_annee"]
        id_annee_uuid = id_annee if not isinstance(id_annee, str) else uuid.UUID(str(id_annee))
        get_or_404_tenant(AnneeScolaire, id_annee_uuid)
        canal = data.get("canal", "email")
        auto_envoyer = bool(data.get("auto_envoyer", True))
        result = relancer_arrieres(
            db,
            id_annee_uuid,
            canal=canal,
            auto_envoyer=auto_envoyer,
            school_id=get_current_school_id(),
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
    @require_role("administrateur", "directeur", "agent_comptable")
    def get(self):
        from io import BytesIO

        from openpyxl import Workbook

        id_annee = request.args.get("id_annee")
        if not id_annee:
            return jsonify({"message": "id_annee requis"}), 400

        get_or_404_tenant(AnneeScolaire, id_annee)
        db = get_db()
        rows = list_arrieres(
            db,
            uuid.UUID(id_annee),
            school_id=get_current_school_id(),
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "Arriérés"
        ws.append(["Matricule", "Nom", "Prénom", "Total dû", "Total payé", "Arriéré"])
        for r in rows:
            ws.append([
                r["matricule"],
                r["nom"],
                r["prenom"],
                r["total_du"],
                r["total_paye"],
                r["arriere"],
            ])

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="arrieres.xlsx",
        )
