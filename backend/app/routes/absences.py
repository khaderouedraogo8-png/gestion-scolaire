"""Module 5 — Routes absences et discipline (contrôle d'accès objet)."""
import uuid

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import (
    get_parent_eleve_ids,
    get_teacher_class_ids,
    parent_has_eleve_access,
    require_role,
    teacher_has_eleve_access,
)
from app.extensions import get_db
from app.models import Absence, AnneeScolaire, Eleve, IncidentDisciplinaire, Inscription
from app.schemas.absences import AbsenceSchema, IncidentDisciplinaireSchema
from app.services.envoi_notification import creer_notification
from app.utils.pagination import empty_pagination, paginate_query, pagination_payload, parse_pagination

blp = Blueprint("absences", __name__, url_prefix="/absences", description="Absences et discipline")


def _serialize_absence(db, absence):
    data = AbsenceSchema().dump(absence)
    eleve = db.query(Eleve).filter(Eleve.id == absence.id_eleve).first()
    if eleve:
        data["prenom"] = eleve.prenom
        data["nom"] = eleve.nom
        data["matricule"] = eleve.matricule
        data["eleve"] = {"prenom": eleve.prenom, "nom": eleve.nom, "matricule": eleve.matricule}
    return data


def _serialize_incident(db, incident):
    data = IncidentDisciplinaireSchema().dump(incident)
    eleve = db.query(Eleve).filter(Eleve.id == incident.id_eleve).first()
    if eleve:
        data["prenom"] = eleve.prenom
        data["nom"] = eleve.nom
        data["matricule"] = eleve.matricule
        data["eleve"] = {"prenom": eleve.prenom, "nom": eleve.nom, "matricule": eleve.matricule}
    return data


def _eleve_ids_for_classe(db, id_classe, id_annee=None):
    q = db.query(Inscription.id_eleve).filter(
        Inscription.id_classe == id_classe,
        Inscription.statut.in_(("inscrit", "reinscrit")),
    )
    if id_annee:
        q = q.filter(Inscription.id_annee == id_annee)
    return [r[0] for r in q.all()]


@blp.route("/")
class AbsencesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self):
        db = get_db()
        user = get_current_user()
        q = db.query(Absence)
        id_eleve = request.args.get("id_eleve")
        id_classe = request.args.get("id_classe")
        date_debut = request.args.get("date_debut")
        date_fin = request.args.get("date_fin")

        # Isolation objet : parent → ses enfants ; enseignant → ses classes uniquement
        # (pas de filtre année active : l'affectation classe suffit pour l'autorisation)
        allowed_eleve_ids = None
        if user.role == "parent":
            allowed_eleve_ids = get_parent_eleve_ids(user)
            if not allowed_eleve_ids:
                return jsonify(empty_pagination())
            q = q.filter(Absence.id_eleve.in_(allowed_eleve_ids))
        elif user.role == "enseignant":
            class_ids = get_teacher_class_ids(user)
            if not class_ids:
                return jsonify(empty_pagination())
            allowed_eleve_ids = []
            for cid in class_ids:
                allowed_eleve_ids.extend(_eleve_ids_for_classe(db, cid, id_annee=None))
            allowed_eleve_ids = list(set(allowed_eleve_ids))
            if not allowed_eleve_ids and not id_eleve:
                return jsonify(empty_pagination())
            if allowed_eleve_ids:
                q = q.filter(Absence.id_eleve.in_(allowed_eleve_ids))

        if id_classe:
            cid = uuid.UUID(id_classe)
            if user.role == "enseignant" and cid not in set(get_teacher_class_ids(user)):
                return jsonify({"message": "Accès refusé"}), 403
            inscr_eleve_ids = _eleve_ids_for_classe(db, cid, id_annee=None)
            if not inscr_eleve_ids:
                return jsonify(empty_pagination())
            q = q.filter(Absence.id_eleve.in_(inscr_eleve_ids))

        if id_eleve:
            eid = uuid.UUID(id_eleve)
            # Toujours vérifier l'objet AVANT de renvoyer une liste vide
            if user.role == "parent" and not parent_has_eleve_access(user, eid):
                return jsonify({"message": "Accès refusé"}), 403
            if user.role == "enseignant" and not teacher_has_eleve_access(user, eid):
                return jsonify({"message": "Accès refusé"}), 403
            if allowed_eleve_ids is not None and eid not in allowed_eleve_ids:
                return jsonify({"message": "Accès refusé"}), 403
            q = q.filter(Absence.id_eleve == eid)

        if date_debut:
            q = q.filter(Absence.date_absence >= date_debut)
        if date_fin:
            q = q.filter(Absence.date_absence <= date_fin)
        page, per_page = parse_pagination()
        items, total, pages = paginate_query(
            q.order_by(Absence.date_absence.desc()), page, per_page
        )
        return jsonify(
            pagination_payload(
                [_serialize_absence(db, a) for a in items],
                page=page,
                per_page=per_page,
                total=total,
                pages=pages,
            )
        )

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.arguments(AbsenceSchema)
    @blp.response(201, AbsenceSchema)
    def post(self, data):
        db = get_db()
        user = get_current_user()
        id_eleve = data["id_eleve"]
        if user.role == "enseignant" and not teacher_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé — élève hors de vos classes"}), 403

        absence = Absence(id=uuid.uuid4(), signale_par=user.id, **data)
        db.add(absence)
        db.commit()

        eleve = db.query(Eleve).filter(Eleve.id == id_eleve).first()
        nom_eleve = f"{eleve.prenom} {eleve.nom}" if eleve else "Votre enfant"
        creer_notification(
            canal="email",
            type_notification="absence",
            contenu=f"{nom_eleve} : absence enregistrée le {data['date_absence']}.",
            id_eleve=id_eleve,
        )
        return absence, 201


@blp.route("/<uuid:id_absence>")
class AbsenceDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.arguments(AbsenceSchema)
    def put(self, data, id_absence):
        db = get_db()
        user = get_current_user()
        absence = db.query(Absence).filter(Absence.id == id_absence).first()
        if not absence:
            return jsonify({"message": "Absence introuvable"}), 404
        if user.role == "enseignant" and not teacher_has_eleve_access(user, absence.id_eleve):
            return jsonify({"message": "Accès refusé"}), 403
        for key, value in data.items():
            if key not in ("id_eleve",):
                setattr(absence, key, value)
        db.commit()
        return jsonify(_serialize_absence(db, absence))


@blp.route("/discipline")
class DisciplineResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        db = get_db()
        user = get_current_user()
        q = db.query(IncidentDisciplinaire)
        id_eleve = request.args.get("id_eleve")

        if user.role == "enseignant":
            class_ids = get_teacher_class_ids(user)
            if not class_ids:
                return jsonify(empty_pagination())
            annee = db.query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
            allowed = []
            for cid in class_ids:
                allowed.extend(_eleve_ids_for_classe(db, cid, annee.id if annee else None))
            if not allowed:
                return jsonify(empty_pagination())
            q = q.filter(IncidentDisciplinaire.id_eleve.in_(set(allowed)))

        if id_eleve:
            eid = uuid.UUID(id_eleve)
            if user.role == "enseignant" and not teacher_has_eleve_access(user, eid):
                return jsonify({"message": "Accès refusé"}), 403
            q = q.filter(IncidentDisciplinaire.id_eleve == eid)
        page, per_page = parse_pagination()
        items, total, pages = paginate_query(
            q.order_by(IncidentDisciplinaire.date_incident.desc()), page, per_page
        )
        return jsonify(
            pagination_payload(
                [_serialize_incident(db, i) for i in items],
                page=page,
                per_page=per_page,
                total=total,
                pages=pages,
            )
        )

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.arguments(IncidentDisciplinaireSchema)
    @blp.response(201, IncidentDisciplinaireSchema)
    def post(self, data):
        db = get_db()
        user = get_current_user()
        if user.role == "enseignant" and not teacher_has_eleve_access(user, data["id_eleve"]):
            return jsonify({"message": "Accès refusé — élève hors de vos classes"}), 403
        incident = IncidentDisciplinaire(id=uuid.uuid4(), declare_par=user.id, **data)
        db.add(incident)
        db.commit()
        return incident, 201
