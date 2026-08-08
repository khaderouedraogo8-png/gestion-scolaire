"""Module 5 — Routes absences et discipline."""
import uuid

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import get_parent_eleve_ids, require_role
from app.extensions import get_db
from app.models import Absence, Eleve, IncidentDisciplinaire, Inscription
from app.schemas.absences import AbsenceSchema, IncidentDisciplinaireSchema
from app.services.envoi_notification import creer_notification

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
        if user.role == "parent":
            eleve_ids = get_parent_eleve_ids(user)
            if not eleve_ids:
                return jsonify([])
            q = q.filter(Absence.id_eleve.in_(eleve_ids))
        if id_classe:
            from app.models import AnneeScolaire

            annee = db.query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
            if annee:
                inscr_eleve_ids = [
                    r[0]
                    for r in db.query(Inscription.id_eleve)
                    .filter(
                        Inscription.id_classe == uuid.UUID(id_classe),
                        Inscription.id_annee == annee.id,
                        Inscription.statut.in_(("inscrit", "reinscrit")),
                    )
                    .all()
                ]
                if not inscr_eleve_ids:
                    return jsonify([])
                q = q.filter(Absence.id_eleve.in_(inscr_eleve_ids))
        if id_eleve:
            q = q.filter(Absence.id_eleve == uuid.UUID(id_eleve))
        if date_debut:
            q = q.filter(Absence.date_absence >= date_debut)
        if date_fin:
            q = q.filter(Absence.date_absence <= date_fin)
        absences = q.order_by(Absence.date_absence.desc()).all()
        return jsonify([_serialize_absence(db, a) for a in absences])

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.arguments(AbsenceSchema)
    @blp.response(201, AbsenceSchema)
    def post(self, data):
        db = get_db()
        user = get_current_user()
        absence = Absence(id=uuid.uuid4(), signale_par=user.id, **data)
        db.add(absence)
        db.commit()

        eleve = db.query(Eleve).filter(Eleve.id == data["id_eleve"]).first()
        nom_eleve = f"{eleve.prenom} {eleve.nom}" if eleve else "Votre enfant"
        creer_notification(
            canal="email",
            type_notification="absence",
            contenu=f"{nom_eleve} : absence enregistrée le {data['date_absence']}.",
            id_eleve=data["id_eleve"],
        )
        return absence, 201


@blp.route("/<uuid:id_absence>")
class AbsenceDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.arguments(AbsenceSchema)
    def put(self, data, id_absence):
        db = get_db()
        absence = db.query(Absence).filter(Absence.id == id_absence).first()
        if not absence:
            return jsonify({"message": "Absence introuvable"}), 404
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
        q = db.query(IncidentDisciplinaire)
        id_eleve = request.args.get("id_eleve")
        if id_eleve:
            q = q.filter(IncidentDisciplinaire.id_eleve == uuid.UUID(id_eleve))
        incidents = q.order_by(IncidentDisciplinaire.date_incident.desc()).all()
        return jsonify([_serialize_incident(db, i) for i in incidents])

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.arguments(IncidentDisciplinaireSchema)
    @blp.response(201, IncidentDisciplinaireSchema)
    def post(self, data):
        db = get_db()
        user = get_current_user()
        incident = IncidentDisciplinaire(id=uuid.uuid4(), declare_par=user.id, **data)
        db.add(incident)
        db.commit()
        return incident, 201
