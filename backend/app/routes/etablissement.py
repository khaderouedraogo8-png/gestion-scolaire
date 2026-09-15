"""Routes établissement, année, programmes, périodes, niveaux, classes."""
import uuid

from flask import abort, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import (
    AnneeScolaire,
    Classe,
    Etablissement,
    EvenementCalendrier,
    NiveauEtude,
    Program,
)
from app.schemas.etablissement import (
    AnneeScolaireSchema,
    ClasseSchema,
    EtablissementSchema,
    NiveauEtudeSchema,
    PeriodCreateSchema,
    PeriodUpdateSchema,
    ProgramCreateSchema,
    ProgramUpdateSchema,
    TrimestreSchema,
)
from app.schemas.pedagogie import EvenementCalendrierSchema
from app.services import academic as academic_service
from app.services.tenant import (
    apply_tenant_school,
    get_current_school_id,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)
from app.utils.pagination import pagination_payload, parse_pagination

blp = Blueprint(
    "etablissement",
    __name__,
    url_prefix="/etablissement",
    description="Configuration établissement",
)


def _evenements_tenant_query(db):
    return (
        db.query(EvenementCalendrier)
        .join(AnneeScolaire, EvenementCalendrier.id_annee == AnneeScolaire.id)
        .filter(AnneeScolaire.school_id == get_current_school_id())
    )


def _get_evenement_or_404(db, id_evenement):
    event = _evenements_tenant_query(db).filter(EvenementCalendrier.id == id_evenement).first()
    if event is None:
        abort(404)
    return event


# ---------------------------------------------------------------------------
# Établissement / Années
# ---------------------------------------------------------------------------


@blp.route("/")
class EtablissementResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
    @blp.response(200, EtablissementSchema)
    def get(self):
        etab = tenant_query(Etablissement).first()
        if not etab:
            return jsonify({"message": "Établissement non configuré"}), 404
        return etab

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(EtablissementSchema)
    @blp.response(201, EtablissementSchema)
    def post(self, data):
        db = get_db()
        reject_client_school_id(data)
        if tenant_query(Etablissement).first():
            return jsonify({"message": "Établissement déjà configuré pour cette école"}), 409
        etab = apply_tenant_school(Etablissement(id=uuid.uuid4(), **data))
        db.add(etab)
        db.commit()
        return etab, 201

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(EtablissementSchema)
    @blp.response(200, EtablissementSchema)
    def put(self, data):
        db = get_db()
        reject_client_school_id(data)
        etab = tenant_query(Etablissement).first()
        if not etab:
            return jsonify({"message": "Établissement non configuré"}), 404
        for key, value in data.items():
            setattr(etab, key, value)
        db.commit()
        return etab


@blp.route("/annees")
class AnneesResource(MethodView):
    @jwt_required()
    @require_role(
        "administrateur", "directeur", "secretariat", "enseignant", "agent_comptable", "parent"
    )
    @blp.response(200, AnneeScolaireSchema(many=True))
    def get(self):
        return tenant_query(AnneeScolaire).order_by(AnneeScolaire.date_debut.desc()).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(AnneeScolaireSchema)
    @blp.response(201, AnneeScolaireSchema)
    def post(self, data):
        db = get_db()
        reject_client_school_id(data)
        if data.get("est_active"):
            tenant_query(AnneeScolaire).update({"est_active": False})
        annee = apply_tenant_school(AnneeScolaire(id=uuid.uuid4(), **data))
        db.add(annee)
        db.commit()
        return annee, 201


@blp.route("/annees/<uuid:id_annee>")
class AnneeDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(AnneeScolaireSchema)
    @blp.response(200, AnneeScolaireSchema)
    def put(self, data, id_annee):
        db = get_db()
        reject_client_school_id(data)
        annee = get_or_404_tenant(AnneeScolaire, id_annee)
        if data.get("est_active"):
            tenant_query(AnneeScolaire).update({"est_active": False})
        for key, value in data.items():
            setattr(annee, key, value)
        db.commit()
        return annee


# ---------------------------------------------------------------------------
# Programs (canonique)
# ---------------------------------------------------------------------------


@blp.route("/programs")
class ProgramsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
    def get(self):
        db = get_db()
        page, per_page = parse_pagination()
        is_active = academic_service._parse_bool_arg(request.args.get("is_active"))
        search = request.args.get("search")
        items, total, pages = academic_service.list_programs(
            db,
            is_active=is_active,
            search=search,
            page=page,
            per_page=per_page,
        )
        return jsonify(
            pagination_payload(items, page=page, per_page=per_page, total=total, pages=pages)
        )

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(ProgramCreateSchema)
    def post(self, data):
        db = get_db()
        reject_client_school_id(request.get_json(silent=True) or {})
        result = academic_service.create_program(db, data)
        return jsonify(result), 201


@blp.route("/programs/<uuid:id_program>")
class ProgramDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
    def get(self, id_program):
        db = get_db()
        return jsonify(academic_service.get_program(db, id_program))

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(ProgramUpdateSchema)
    def patch(self, data, id_program):
        db = get_db()
        return jsonify(academic_service.update_program(db, id_program, data))


@blp.route("/programs/<uuid:id_program>/deactivate")
class ProgramDeactivate(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def post(self, id_program):
        db = get_db()
        return jsonify(academic_service.deactivate_program(db, id_program))


# ---------------------------------------------------------------------------
# Périodes (canonique) — même service que /trimestres
# ---------------------------------------------------------------------------


@blp.route("/periodes")
class PeriodesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self):
        db = get_db()
        page, per_page = parse_pagination()
        id_program = request.args.get("id_program") or request.args.get("program_id")
        id_annee = request.args.get("id_annee") or request.args.get("academic_year_id")
        period_type = request.args.get("period_type")
        is_active = academic_service._parse_bool_arg(request.args.get("is_active"))

        items, total, pages = academic_service.list_periods(
            db,
            id_program=uuid.UUID(id_program) if id_program else None,
            id_annee=uuid.UUID(id_annee) if id_annee else None,
            period_type=period_type,
            is_active=is_active,
            page=page,
            per_page=per_page,
        )
        payload = [academic_service.serialize_period(p) for p in items]
        return jsonify(
            pagination_payload(payload, page=page, per_page=per_page, total=total or 0, pages=pages or 0)
        )

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(PeriodCreateSchema)
    def post(self, data):
        db = get_db()
        period = academic_service.create_period(db, data)
        return jsonify(academic_service.serialize_period(period)), 201


@blp.route("/periodes/<uuid:id_periode>")
class PeriodeDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self, id_periode):
        db = get_db()
        period = academic_service.get_period(db, id_periode)
        return jsonify(academic_service.serialize_period(period))

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(PeriodUpdateSchema)
    def patch(self, data, id_periode):
        db = get_db()
        period = academic_service.update_period(db, id_periode, data)
        return jsonify(academic_service.serialize_period(period))


@blp.route("/periodes/<uuid:id_periode>/deactivate")
class PeriodeDeactivate(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def post(self, id_periode):
        db = get_db()
        period = academic_service.deactivate_period(db, id_periode)
        return jsonify(academic_service.serialize_period(period))


# ---------------------------------------------------------------------------
# Trimestres — façade legacy → AcademicPeriodService
# ---------------------------------------------------------------------------


@blp.route("/trimestres")
class TrimestresResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    @blp.response(200, TrimestreSchema(many=True))
    def get(self):
        db = get_db()
        id_annee = request.args.get("id_annee")
        items, _, _ = academic_service.list_periods(
            db,
            id_annee=uuid.UUID(id_annee) if id_annee else None,
            page=None,
            per_page=None,
        )
        return items

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(TrimestreSchema)
    @blp.response(201, TrimestreSchema)
    def post(self, data):
        db = get_db()
        # Façade : numero → sequence via create_period
        return academic_service.create_period(db, data), 201


@blp.route("/trimestres/<uuid:id_trimestre>")
class TrimestreDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(TrimestreSchema)
    @blp.response(200, TrimestreSchema)
    def put(self, data, id_trimestre):
        db = get_db()
        return academic_service.update_period(db, id_trimestre, data)

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_trimestre):
        db = get_db()
        # Soft-deactivate (pas de hard delete destructif)
        academic_service.deactivate_period(db, id_trimestre)
        return jsonify({"message": "Trimestre désactivé"})


# ---------------------------------------------------------------------------
# Niveaux / Classes
# ---------------------------------------------------------------------------


@blp.route("/niveaux")
class NiveauxResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
    @blp.response(200, NiveauEtudeSchema(many=True))
    def get(self):
        q = tenant_query(NiveauEtude)
        id_program = request.args.get("id_program") or request.args.get("program_id")
        if id_program:
            get_or_404_tenant(Program, id_program)
            q = q.filter(NiveauEtude.id_program == uuid.UUID(id_program))
        return q.order_by(NiveauEtude.ordre).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(NiveauEtudeSchema)
    @blp.response(201, NiveauEtudeSchema)
    def post(self, data):
        db = get_db()
        reject_client_school_id(data)
        payload = dict(data)
        payload["id_program"] = academic_service.resolve_niveau_program_id(
            db, payload, get_current_school_id()
        )
        niveau = apply_tenant_school(NiveauEtude(id=uuid.uuid4(), **payload))
        db.add(niveau)
        db.commit()
        return niveau, 201


@blp.route("/classes")
class ClassesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
    def get(self):
        from app.auth.jwt_handler import get_current_user
        from app.auth.permissions import get_teacher_class_ids
        from app.services.classes_navigation import get_classes_navigation

        db = get_db()
        user = get_current_user()
        id_annee = request.args.get("id_annee")
        id_program = request.args.get("id_program") or request.args.get("program_id")
        cycle = request.args.get("cycle")
        enriched = request.args.get("enriched", "").lower() in ("1", "true", "yes")

        if id_annee:
            get_or_404_tenant(AnneeScolaire, id_annee)
            annee_uuid = uuid.UUID(id_annee)
        else:
            active = tenant_query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
            annee_uuid = active.id if active else None
        class_ids = None
        if user.role == "enseignant":
            class_ids = get_teacher_class_ids(user)

        if enriched or cycle:
            return jsonify(
                get_classes_navigation(
                    db,
                    cycle=cycle,
                    id_annee=annee_uuid,
                    class_ids=class_ids,
                )
            )

        q = tenant_query(Classe)
        if annee_uuid:
            q = q.filter(Classe.id_annee == annee_uuid)
        if id_program:
            get_or_404_tenant(Program, id_program)
            q = q.filter(Classe.id_program == uuid.UUID(id_program))
        if class_ids is not None:
            if not class_ids:
                return jsonify([])
            q = q.filter(Classe.id.in_(class_ids))
        return jsonify([ClasseSchema().dump(c) for c in q.all()])

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(ClasseSchema)
    @blp.response(201, ClasseSchema)
    def post(self, data):
        db = get_db()
        reject_client_school_id(data)
        get_or_404_tenant(AnneeScolaire, data["id_annee"])
        get_or_404_tenant(NiveauEtude, data["id_niveau"])
        payload = dict(data)
        payload["id_program"] = academic_service.resolve_classe_program_id(db, payload)
        classe = apply_tenant_school(Classe(id=uuid.uuid4(), **payload))
        db.add(classe)
        db.commit()
        return classe, 201


@blp.route("/classes/<uuid:id_classe>")
class ClasseDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(ClasseSchema)
    @blp.response(200, ClasseSchema)
    def put(self, data, id_classe):
        db = get_db()
        reject_client_school_id(data)
        classe = get_or_404_tenant(Classe, id_classe)
        payload = dict(data)
        if "id_annee" in payload:
            get_or_404_tenant(AnneeScolaire, payload["id_annee"])
        if "id_niveau" in payload:
            get_or_404_tenant(NiveauEtude, payload["id_niveau"])
            payload["id_program"] = academic_service.resolve_classe_program_id(
                db, {**payload, "id_niveau": payload["id_niveau"]}
            )
        for key, value in payload.items():
            setattr(classe, key, value)
        db.commit()
        return classe


# ---------------------------------------------------------------------------
# Calendrier
# ---------------------------------------------------------------------------


@blp.route("/calendrier")
class CalendrierResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self):
        db = get_db()
        id_annee = request.args.get("id_annee")
        if not id_annee:
            return jsonify({"message": "id_annee requis"}), 400
        get_or_404_tenant(AnneeScolaire, id_annee)
        rows = (
            _evenements_tenant_query(db)
            .filter(EvenementCalendrier.id_annee == uuid.UUID(id_annee))
            .order_by(EvenementCalendrier.date_debut)
            .all()
        )
        return jsonify([EvenementCalendrierSchema().dump(r) for r in rows])

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(EvenementCalendrierSchema)
    def post(self, data):
        db = get_db()
        if data["date_fin"] < data["date_debut"]:
            return jsonify({"message": "La date de fin doit être après la date de début"}), 400
        get_or_404_tenant(AnneeScolaire, data["id_annee"])
        event = EvenementCalendrier(id=uuid.uuid4(), **data)
        db.add(event)
        db.commit()
        return EvenementCalendrierSchema().dump(event), 201


@blp.route("/calendrier/<uuid:id_evenement>")
class CalendrierDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(EvenementCalendrierSchema)
    def put(self, data, id_evenement):
        db = get_db()
        event = _get_evenement_or_404(db, id_evenement)
        if data["date_fin"] < data["date_debut"]:
            return jsonify({"message": "La date de fin doit être après la date de début"}), 400
        if "id_annee" in data:
            get_or_404_tenant(AnneeScolaire, data["id_annee"])
        for key, value in data.items():
            setattr(event, key, value)
        db.commit()
        return EvenementCalendrierSchema().dump(event)

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_evenement):
        db = get_db()
        event = _get_evenement_or_404(db, id_evenement)
        db.delete(event)
        db.commit()
        return jsonify({"message": "Événement supprimé"})
