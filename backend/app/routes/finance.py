"""Module 3 — Routes finance : frais, échéances, paiements, SYSCOHADA, intégrations."""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from flask import abort, jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

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
    Inscription,
    NiveauEtude,
    Paiement,
    PlanComptableSyscohada,
)
from app.schemas.finance import (
    AnnulationPaiementSchema,
    EcheancePaiementSchema,
    FraisScolaireSchema,
    FraisWithEcheancesSchema,
    PaiementCreateSchema,
    PaiementSchema,
    RelanceArrieresSchema,
)
from app.services.channels.mobile_money import mobile_money_status
from app.services.channels.whatsapp import whatsapp_status
from app.services.envoi_notification import creer_notification
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
from app.utils.errors import abort_api
from app.utils.pagination import empty_pagination, paginate_query, pagination_payload, parse_pagination

blp = Blueprint("finance", __name__, url_prefix="/finance", description="Finance et comptabilité")

_SYSCOHADA_SEED = [
    ("7011", "Frais de scolarité", "7"),
    ("7012", "Frais d'inscription", "7"),
    ("7013", "Frais d'examen", "7"),
    ("521", "Banque", "5"),
    ("571", "Caisse", "5"),
    ("4111", "Élèves — clients", "4"),
]


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


def _assert_no_duplicate_frais(db, id_niveau, id_annee, motif, school_id):
    existing = (
        tenant_query(FraisScolaire)
        .filter(
            FraisScolaire.id_niveau == id_niveau,
            FraisScolaire.id_annee == id_annee,
            FraisScolaire.motif == motif,
        )
        .first()
    )
    if existing:
        abort_api(
            409,
            "FRAIS_DUPLICATE",
            "Un frais avec le même motif existe déjà pour ce niveau et cette année.",
        )


def _build_tranches(montant_total: Decimal, nb: int, start: date | None = None) -> list[dict]:
    start = start or date.today()
    cents = int(Decimal(montant_total) * 100)
    base, rem = divmod(cents, nb)
    parts = []
    for i in range(nb):
        part_cents = base + (1 if i < rem else 0)
        parts.append({
            "libelle": f"Tranche {i + 1}/{nb}",
            "montant": Decimal(part_cents) / 100,
            "date_echeance": start + timedelta(days=30 * i),
        })
    return parts


def _notify_parent_recu(paiement: Paiement, canal: str = "email") -> None:
    contenu = (
        f"Paiement enregistré — reçu {paiement.numero_recu} : "
        f"{float(paiement.montant_verse):,.0f} FCFA ({paiement.motif})."
    )
    try:
        creer_notification(
            canal=canal,
            type_notification="recu_paiement",
            contenu=contenu,
            id_eleve=paiement.id_eleve,
            school_id=paiement.school_id,
            idempotency_key=f"recu:{canal}:{paiement.id}",
        )
    except Exception:
        # Ne bloque jamais l'encaissement si la notif échoue
        db = get_db()
        try:
            db.rollback()
        except Exception:
            pass


@blp.route("/integrations")
class FinanceIntegrations(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    def get(self):
        wa = whatsapp_status()
        mm = mobile_money_status()
        return jsonify({
            "whatsapp": {
                "configured": wa.configured,
                "status": wa.status,
                "message": wa.message,
            },
            "mobile_money": {
                "configured": mm.configured,
                "status": mm.status,
                "message": mm.message,
                "operators": mm.operators,
            },
        })


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
        _assert_no_duplicate_frais(
            db, data["id_niveau"], data["id_annee"], data["motif"], get_current_school_id()
        )
        frais = FraisScolaire(id=uuid.uuid4(), **data)
        apply_tenant_school(frais)
        try:
            db.add(frais)
            db.commit()
        except IntegrityError:
            db.rollback()
            abort_api(409, "FRAIS_DUPLICATE", "Frais déjà existant (contrainte d'unicité).")
        return frais, 201


@blp.route("/frais/with-echeances")
class FraisWithEcheances(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(FraisWithEcheancesSchema)
    def post(self, data):
        """Crée un frais + échéances fractionnées (1/3/4/6 ou liste explicite)."""
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        niveau = get_or_404_tenant(NiveauEtude, data["id_niveau"])
        annee = get_or_404_tenant(AnneeScolaire, data["id_annee"])
        assert_same_school(niveau, annee)
        _assert_no_duplicate_frais(
            db, data["id_niveau"], data["id_annee"], data["motif"], get_current_school_id()
        )

        montant = Decimal(str(data["montant_total"]))
        echeances_in = data.get("echeances")
        nb = data.get("nb_tranches")
        if echeances_in:
            parts = echeances_in
        elif nb:
            parts = _build_tranches(montant, int(nb))
        else:
            parts = _build_tranches(montant, 3)

        total_parts = sum(Decimal(str(p["montant"])) for p in parts)
        if abs(total_parts - montant) > Decimal("0.05"):
            abort_api(
                400,
                "ECHEANCES_SUM_MISMATCH",
                f"La somme des échéances ({total_parts}) doit égaler le montant total ({montant}).",
            )

        frais = FraisScolaire(
            id=uuid.uuid4(),
            id_niveau=data["id_niveau"],
            id_annee=data["id_annee"],
            motif=data["motif"],
            montant_total=montant,
        )
        apply_tenant_school(frais)
        db.add(frais)
        db.flush()
        for p in parts:
            db.add(
                EcheancePaiement(
                    id=uuid.uuid4(),
                    id_frais=frais.id,
                    libelle=p.get("libelle"),
                    montant=Decimal(str(p["montant"])),
                    date_echeance=p["date_echeance"],
                )
            )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            abort_api(409, "FRAIS_DUPLICATE", "Frais ou échéance en doublon.")
        return jsonify(_serialize_frais(db, frais)), 201


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
        return q.order_by(EcheancePaiement.date_echeance).all()

    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    @blp.arguments(EcheancePaiementSchema)
    @blp.response(201, EcheancePaiementSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        get_or_404_tenant(FraisScolaire, data["id_frais"])
        echeance = EcheancePaiement(id=uuid.uuid4(), **data)
        try:
            db.add(echeance)
            db.commit()
        except IntegrityError:
            db.rollback()
            abort_api(
                409,
                "ECHEANCE_DUPLICATE",
                "Une échéance avec le même libellé et la même date existe déjà.",
            )
        return echeance, 201


@blp.route("/echeances/eleve")
class EcheancesEleve(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable", "parent")
    def get(self):
        """Échéances applicables à un élève (via niveau de sa classe) pour une année."""
        db = get_db()
        user = get_current_user()
        id_eleve = request.args.get("id_eleve")
        id_annee = request.args.get("id_annee")
        if not id_eleve or not id_annee:
            return jsonify({"message": "id_eleve et id_annee requis"}), 400
        eid = uuid.UUID(id_eleve)
        aid = uuid.UUID(id_annee)
        eleve = get_or_404_tenant(Eleve, eid)
        get_or_404_tenant(AnneeScolaire, aid)
        if user.role == "parent" and not parent_has_eleve_access(user, eid):
            return jsonify({"message": "Accès refusé"}), 403

        insc = (
            tenant_query(Inscription)
            .filter(
                Inscription.id_eleve == eid,
                Inscription.id_annee == aid,
                Inscription.statut.in_(("inscrit", "reinscrit")),
            )
            .first()
        )
        if not insc:
            return jsonify([])
        classe = get_or_404_tenant(Classe, insc.id_classe)
        frais_list = (
            tenant_query(FraisScolaire)
            .filter(
                FraisScolaire.id_niveau == classe.id_niveau,
                FraisScolaire.id_annee == aid,
            )
            .all()
        )
        out = []
        for frais in frais_list:
            for ec in (
                _tenant_echeance_query(db)
                .filter(EcheancePaiement.id_frais == frais.id)
                .order_by(EcheancePaiement.date_echeance)
                .all()
            ):
                out.append({
                    **EcheancePaiementSchema().dump(ec),
                    "motif_frais": frais.motif,
                    "montant": float(ec.montant),
                })
        return jsonify(out)


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
        log_audit(
            "PAIEMENT_ENCAISSE",
            user.id,
            "paiement",
            paiement.id,
            {"montant": str(data["montant_verse"])},
        )

        # Reçu PDF + notification parent (email par défaut)
        try:
            generer_recu_pdf(paiement.id)
        except Exception:
            pass
        _notify_parent_recu(paiement, canal="email")
        # Inbox interne parent
        _notify_parent_recu(paiement, canal="interne")

        return jsonify(_serialize_paiement(db, paiement)), 201


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
        paiement.annule = True
        paiement.motif_annulation = data["motif_annulation"]
        db.commit()
        log_audit(
            "PAIEMENT_ANNULE",
            user.id,
            "paiement",
            paiement.id,
            {"motif": data["motif_annulation"]},
        )
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
        return jsonify([{**a, "id_eleve": str(a["id_eleve"])} for a in arrieres])


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
        if canal == "whatsapp" and not whatsapp_status().configured:
            abort_api(
                400,
                "WHATSAPP_NON_CONFIGURE",
                "WhatsApp non configuré — choisissez email ou sms, ou configurez WHATSAPP_*.",
            )
        auto_envoyer = bool(data.get("auto_envoyer", True))
        mode = data.get("mode", "calendaire")
        result = relancer_arrieres(
            db,
            id_annee_uuid,
            canal=canal,
            auto_envoyer=auto_envoyer,
            school_id=get_current_school_id(),
            mode=mode,
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


@blp.route("/syscohada/plan")
class SyscohadaPlan(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    def get(self):
        """Plan comptable SYSCOHADA (skeleton) — seed auto si vide."""
        db = get_db()
        school_id = get_current_school_id()
        rows = (
            db.query(PlanComptableSyscohada)
            .filter(PlanComptableSyscohada.school_id == school_id)
            .order_by(PlanComptableSyscohada.compte)
            .all()
        )
        if not rows:
            for compte, libelle, classe in _SYSCOHADA_SEED:
                db.add(
                    PlanComptableSyscohada(
                        id=uuid.uuid4(),
                        school_id=school_id,
                        compte=compte,
                        libelle=libelle,
                        classe=classe,
                        actif=True,
                    )
                )
            db.commit()
            rows = (
                db.query(PlanComptableSyscohada)
                .filter(PlanComptableSyscohada.school_id == school_id)
                .order_by(PlanComptableSyscohada.compte)
                .all()
            )
        return jsonify([
            {
                "id": str(r.id),
                "compte": r.compte,
                "libelle": r.libelle,
                "classe": r.classe,
                "actif": r.actif,
            }
            for r in rows
        ])
