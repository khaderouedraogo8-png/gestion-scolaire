"""Routes établissement, année scolaire, trimestre, niveau, classe."""
import uuid

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import AnneeScolaire, Classe, Etablissement, NiveauEtude, Trimestre
from app.schemas.etablissement import (
    AnneeScolaireSchema,
    ClasseSchema,
    EtablissementSchema,
    NiveauEtudeSchema,
    TrimestreSchema,
)

blp = Blueprint("etablissement", __name__, url_prefix="/etablissement", description="Configuration établissement")


@blp.route("/")
class EtablissementResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
    @blp.response(200, EtablissementSchema)
    def get(self):
        db = get_db()
        etab = db.query(Etablissement).first()
        if not etab:
            return jsonify({"message": "Établissement non configuré"}), 404
        return etab

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(EtablissementSchema)
    @blp.response(201, EtablissementSchema)
    def post(self, data):
        db = get_db()
        existing = db.query(Etablissement).first()
        if existing:
            return jsonify({"message": "Établissement déjà configuré (mono-établissement)"}), 409
        etab = Etablissement(id=uuid.uuid4(), **data)
        db.add(etab)
        db.commit()
        return etab, 201

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(EtablissementSchema)
    @blp.response(200, EtablissementSchema)
    def put(self, data):
        db = get_db()
        etab = db.query(Etablissement).first()
        if not etab:
            return jsonify({"message": "Établissement non configuré"}), 404
        for key, value in data.items():
            setattr(etab, key, value)
        db.commit()
        return etab


@blp.route("/annees")
class AnneesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
    @blp.response(200, AnneeScolaireSchema(many=True))
    def get(self):
        db = get_db()
        return db.query(AnneeScolaire).order_by(AnneeScolaire.date_debut.desc()).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(AnneeScolaireSchema)
    @blp.response(201, AnneeScolaireSchema)
    def post(self, data):
        db = get_db()
        if data.get("est_active"):
            db.query(AnneeScolaire).update({"est_active": False})
        annee = AnneeScolaire(id=uuid.uuid4(), **data)
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
        annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == id_annee).first()
        if not annee:
            return jsonify({"message": "Année introuvable"}), 404
        if data.get("est_active"):
            db.query(AnneeScolaire).update({"est_active": False})
        for key, value in data.items():
            setattr(annee, key, value)
        db.commit()
        return annee


@blp.route("/trimestres")
class TrimestresResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.response(200, TrimestreSchema(many=True))
    def get(self):
        db = get_db()
        id_annee = request.args.get("id_annee")
        q = db.query(Trimestre)
        if id_annee:
            q = q.filter(Trimestre.id_annee == uuid.UUID(id_annee))
        return q.order_by(Trimestre.numero).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(TrimestreSchema)
    @blp.response(201, TrimestreSchema)
    def post(self, data):
        db = get_db()
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
        trim = db.query(Trimestre).filter(Trimestre.id == id_trimestre).first()
        if not trim:
            return jsonify({"message": "Trimestre introuvable"}), 404
        for key, value in data.items():
            setattr(trim, key, value)
        db.commit()
        return trim

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_trimestre):
        db = get_db()
        trim = db.query(Trimestre).filter(Trimestre.id == id_trimestre).first()
        if not trim:
            return jsonify({"message": "Trimestre introuvable"}), 404
        db.delete(trim)
        db.commit()
        return jsonify({"message": "Trimestre supprimé"})


@blp.route("/niveaux")
class NiveauxResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
    @blp.response(200, NiveauEtudeSchema(many=True))
    def get(self):
        db = get_db()
        return db.query(NiveauEtude).order_by(NiveauEtude.ordre).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(NiveauEtudeSchema)
    @blp.response(201, NiveauEtudeSchema)
    def post(self, data):
        db = get_db()
        niveau = NiveauEtude(id=uuid.uuid4(), **data)
        db.add(niveau)
        db.commit()
        return niveau, 201


@blp.route("/classes")
class ClassesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
    @blp.response(200, ClasseSchema(many=True))
    def get(self):
        from flask import request
        db = get_db()
        q = db.query(Classe)
        id_annee = request.args.get("id_annee")
        if id_annee:
            q = q.filter(Classe.id_annee == uuid.UUID(id_annee))
        return q.all()

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(ClasseSchema)
    @blp.response(201, ClasseSchema)
    def post(self, data):
        db = get_db()
        classe = Classe(id=uuid.uuid4(), **data)
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
        classe = db.query(Classe).filter(Classe.id == id_classe).first()
        if not classe:
            return jsonify({"message": "Classe introuvable"}), 404
        for key, value in data.items():
            setattr(classe, key, value)
        db.commit()
        return classe
