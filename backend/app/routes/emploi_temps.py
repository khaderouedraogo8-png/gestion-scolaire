"""Module 4 — Routes emploi du temps, enseignants, affectations."""
import uuid

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import (
    AffectationEnseignant,
    Classe,
    CreneauEmploiTemps,
    Enseignant,
    Matiere,
    Salle,
)
from app.schemas.emploi_temps import (
    AffectationEnseignantSchema,
    CreneauEmploiTempsSchema,
    EnseignantSchema,
    SalleSchema,
)

blp = Blueprint("emploi_temps", __name__, url_prefix="/emploi-temps", description="Emploi du temps")

JOURS = {1: "Lundi", 2: "Mardi", 3: "Mercredi", 4: "Jeudi", 5: "Vendredi", 6: "Samedi", 7: "Dimanche"}


def _serialize_affectation(db, aff):
    data = AffectationEnseignantSchema().dump(aff)
    ens = db.query(Enseignant).filter(Enseignant.id == aff.id_enseignant).first()
    cls = db.query(Classe).filter(Classe.id == aff.id_classe).first()
    mat = db.query(Matiere).filter(Matiere.id == aff.id_matiere).first()
    data["enseignant_nom"] = f"{ens.prenom} {ens.nom}" if ens else None
    data["classe_nom"] = cls.libelle if cls else None
    data["matiere_nom"] = mat.libelle if mat else None
    if ens:
        data["enseignant"] = {"prenom": ens.prenom, "nom": ens.nom}
    if cls:
        data["classe"] = {"libelle": cls.libelle}
    if mat:
        data["matiere"] = {"libelle": mat.libelle}
    return data


def _serialize_creneau(db, creneau):
    data = CreneauEmploiTempsSchema().dump(creneau)
    data["jour_libelle"] = JOURS.get(creneau.jour_semaine, str(creneau.jour_semaine))
    data["heure_debut"] = creneau.heure_debut.strftime("%H:%M") if creneau.heure_debut else None
    data["heure_fin"] = creneau.heure_fin.strftime("%H:%M") if creneau.heure_fin else None
    aff = db.query(AffectationEnseignant).filter(
        AffectationEnseignant.id == creneau.id_affectation
    ).first()
    if aff:
        data.update(_serialize_affectation(db, aff))
    if creneau.id_salle:
        salle = db.query(Salle).filter(Salle.id == creneau.id_salle).first()
        data["salle_libelle"] = salle.libelle if salle else None
    return data


@blp.route("/enseignants")
class EnseignantsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.response(200, EnseignantSchema(many=True))
    def get(self):
        db = get_db()
        return db.query(Enseignant).order_by(Enseignant.nom).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(EnseignantSchema)
    @blp.response(201, EnseignantSchema)
    def post(self, data):
        db = get_db()
        enseignant = Enseignant(id=uuid.uuid4(), **data)
        db.add(enseignant)
        db.commit()
        return enseignant, 201


@blp.route("/enseignants/<uuid:id_enseignant>")
class EnseignantDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(EnseignantSchema)
    @blp.response(200, EnseignantSchema)
    def put(self, data, id_enseignant):
        db = get_db()
        enseignant = db.query(Enseignant).filter(Enseignant.id == id_enseignant).first()
        if not enseignant:
            return jsonify({"message": "Enseignant introuvable"}), 404
        for key, value in data.items():
            setattr(enseignant, key, value)
        db.commit()
        return enseignant


@blp.route("/affectations")
class AffectationsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        db = get_db()
        q = db.query(AffectationEnseignant)
        id_annee = request.args.get("id_annee")
        id_classe = request.args.get("id_classe")
        id_enseignant = request.args.get("id_enseignant")
        if id_annee:
            q = q.filter(AffectationEnseignant.id_annee == uuid.UUID(id_annee))
        if id_classe:
            q = q.filter(AffectationEnseignant.id_classe == uuid.UUID(id_classe))
        if id_enseignant:
            q = q.filter(AffectationEnseignant.id_enseignant == uuid.UUID(id_enseignant))
        items = [_serialize_affectation(db, a) for a in q.all()]
        return jsonify({"items": items, "total": len(items)})

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(AffectationEnseignantSchema)
    @blp.response(201, AffectationEnseignantSchema)
    def post(self, data):
        db = get_db()
        affectation = AffectationEnseignant(id=uuid.uuid4(), **data)
        db.add(affectation)
        db.commit()
        return affectation, 201


@blp.route("/affectations/<uuid:id_affectation>")
class AffectationDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_affectation):
        db = get_db()
        aff = db.query(AffectationEnseignant).filter(
            AffectationEnseignant.id == id_affectation
        ).first()
        if not aff:
            return jsonify({"message": "Affectation introuvable"}), 404
        db.query(CreneauEmploiTemps).filter(
            CreneauEmploiTemps.id_affectation == id_affectation
        ).delete()
        db.delete(aff)
        db.commit()
        return jsonify({"message": "Affectation supprimée"})


@blp.route("/salles")
class SallesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.response(200, SalleSchema(many=True))
    def get(self):
        db = get_db()
        return db.query(Salle).order_by(Salle.libelle).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(SalleSchema)
    @blp.response(201, SalleSchema)
    def post(self, data):
        db = get_db()
        salle = Salle(id=uuid.uuid4(), **data)
        db.add(salle)
        db.commit()
        return salle, 201


@blp.route("/creneaux")
class CreneauxResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        db = get_db()
        q = db.query(CreneauEmploiTemps)
        id_affectation = request.args.get("id_affectation")
        id_classe = request.args.get("id_classe")
        id_annee = request.args.get("id_annee")
        if id_affectation:
            q = q.filter(CreneauEmploiTemps.id_affectation == uuid.UUID(id_affectation))
        creneaux = q.all()
        if id_classe or id_annee:
            filtered = []
            for c in creneaux:
                aff = db.query(AffectationEnseignant).filter(
                    AffectationEnseignant.id == c.id_affectation
                ).first()
                if not aff:
                    continue
                if id_classe and str(aff.id_classe) != id_classe:
                    continue
                if id_annee and str(aff.id_annee) != id_annee:
                    continue
                filtered.append(c)
            creneaux = filtered
        return jsonify([_serialize_creneau(db, c) for c in creneaux])

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(CreneauEmploiTempsSchema)
    @blp.response(201, CreneauEmploiTempsSchema)
    def post(self, data):
        db = get_db()
        creneau = CreneauEmploiTemps(id=uuid.uuid4(), **data)
        db.add(creneau)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            if "no_chevauchement_salle" in str(e):
                return jsonify({"message": "Conflit de salle — créneau chevauchant"}), 409
            raise
        return creneau, 201


@blp.route("/creneaux/<uuid:id_creneau>")
class CreneauDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(CreneauEmploiTempsSchema)
    @blp.response(200, CreneauEmploiTempsSchema)
    def put(self, data, id_creneau):
        db = get_db()
        creneau = db.query(CreneauEmploiTemps).filter(CreneauEmploiTemps.id == id_creneau).first()
        if not creneau:
            return jsonify({"message": "Créneau introuvable"}), 404
        for key, value in data.items():
            setattr(creneau, key, value)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            if "no_chevauchement_salle" in str(e):
                return jsonify({"message": "Conflit de salle — créneau chevauchant"}), 409
            raise
        return creneau

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_creneau):
        db = get_db()
        creneau = db.query(CreneauEmploiTemps).filter(CreneauEmploiTemps.id == id_creneau).first()
        if not creneau:
            return jsonify({"message": "Créneau introuvable"}), 404
        db.delete(creneau)
        db.commit()
        return jsonify({"message": "Créneau supprimé"})
