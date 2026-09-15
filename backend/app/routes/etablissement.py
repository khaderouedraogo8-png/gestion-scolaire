"""Routes établissement, année scolaire, trimestre, niveau, classe."""
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
    Trimestre,
)
from app.schemas.etablissement import (
    AnneeScolaireSchema,
    ClasseSchema,
    EtablissementSchema,
    NiveauEtudeSchema,
    TrimestreSchema,
)
from app.schemas.pedagogie import EvenementCalendrierSchema
from app.services.tenant import (
    apply_tenant_school,
    get_current_school_id,
    get_or_404_tenant,
    tenant_query,
)

blp = Blueprint("etablissement", __name__, url_prefix="/etablissement", description="Configuration établissement")


def _trimestres_tenant_query(db):
    return (
        db.query(Trimestre)
        .join(AnneeScolaire, Trimestre.id_annee == AnneeScolaire.id)
        .filter(AnneeScolaire.school_id == get_current_school_id())
    )


def _get_trimestre_or_404(db, id_trimestre):
    trim = _trimestres_tenant_query(db).filter(Trimestre.id == id_trimestre).first()
    if trim is None:
        abort(404)
    return trim


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
        annee = get_or_404_tenant(AnneeScolaire, id_annee)
        if data.get("est_active"):
            tenant_query(AnneeScolaire).update({"est_active": False})
        for key, value in data.items():
            setattr(annee, key, value)
        db.commit()
        return annee


@blp.route("/trimestres")
class TrimestresResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    @blp.response(200, TrimestreSchema(many=True))
    def get(self):
        db = get_db()
        id_annee = request.args.get("id_annee")
        q = _trimestres_tenant_query(db)
        if id_annee:
            get_or_404_tenant(AnneeScolaire, id_annee)
            q = q.filter(Trimestre.id_annee == uuid.UUID(id_annee))
        return q.order_by(Trimestre.numero).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(TrimestreSchema)
    @blp.response(201, TrimestreSchema)
    def post(self, data):
        db = get_db()
        get_or_404_tenant(AnneeScolaire, data["id_annee"])
        trim = Trimestre(id=uuid.uuid4(), **data)
        db.add(trim)
        db.commit()
        return trim, 201


@blp.route("/trimestres/<uuid:id_trimestre>")
class TrimestreDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(TrimestreSchema)
    @blp.response(200, TrimestreSchema)
    def put(self, data, id_trimestre):
        db = get_db()
        trim = _get_trimestre_or_404(db, id_trimestre)
        if "id_annee" in data:
            get_or_404_tenant(AnneeScolaire, data["id_annee"])
        for key, value in data.items():
            setattr(trim, key, value)
        db.commit()
        return trim

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_trimestre):
        db = get_db()
        trim = _get_trimestre_or_404(db, id_trimestre)
        db.delete(trim)
        db.commit()
        return jsonify({"message": "Trimestre supprimé"})


@blp.route("/niveaux")
class NiveauxResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
    @blp.response(200, NiveauEtudeSchema(many=True))
    def get(self):
        return tenant_query(NiveauEtude).order_by(NiveauEtude.ordre).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(NiveauEtudeSchema)
    @blp.response(201, NiveauEtudeSchema)
    def post(self, data):
        db = get_db()
        niveau = apply_tenant_school(NiveauEtude(id=uuid.uuid4(), **data))
        db.add(niveau)
        db.commit()
        return niveau, 201


@blp.route("/classes")
class ClassesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
    def get(self):
        from flask import request

        from app.auth.jwt_handler import get_current_user
        from app.auth.permissions import get_teacher_class_ids
        from app.services.classes_navigation import get_classes_navigation

        db = get_db()
        user = get_current_user()
        id_annee = request.args.get("id_annee")
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
        get_or_404_tenant(AnneeScolaire, data["id_annee"])
        get_or_404_tenant(NiveauEtude, data["id_niveau"])
        classe = apply_tenant_school(Classe(id=uuid.uuid4(), **data))
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
        classe = get_or_404_tenant(Classe, id_classe)
        if "id_annee" in data:
            get_or_404_tenant(AnneeScolaire, data["id_annee"])
        if "id_niveau" in data:
            get_or_404_tenant(NiveauEtude, data["id_niveau"])
        for key, value in data.items():
            setattr(classe, key, value)
        db.commit()
        return classe


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
