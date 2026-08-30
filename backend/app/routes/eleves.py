"""Module 1 — Routes élèves, inscriptions, parents."""
import os
import uuid
from datetime import date

from flask import current_app, jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import (
    can_view_medical_notes,
    filter_eleves_by_role,
    parent_has_eleve_access,
    require_role,
)
from app.extensions import get_db
from app.models import (
    AnneeScolaire,
    Classe,
    Eleve,
    EleveParent,
    Etablissement,
    Inscription,
    NiveauEtude,
    ParentTuteur,
)
from app.schemas.eleve import (
    EleveCreateSchema,
    EleveDetailSchema,
    EleveSchema,
    InscriptionCreateSchema,
    InscriptionSchema,
    ParentTuteurSchema,
)
from app.utils.audit_logger import log_audit
from app.utils.chiffrement import chiffrer_notes_medicales, dechiffrer_notes_medicales

blp = Blueprint("eleves", __name__, url_prefix="/eleves", description="Gestion des élèves")


def _generer_matricule(db, id_annee: uuid.UUID) -> str:
    """Génère un matricule selon le format configuré dans etablissement."""
    etab = db.query(Etablissement).first()
    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == id_annee).first()
    format_str = (etab.format_matricule if etab else None) or "{ANNEE}M-{SEQ}"
    annee_court = annee.libelle[:4] if annee else str(date.today().year)
    count = db.query(Eleve).count() + 1
    matricule = format_str.replace("{ANNEE}", annee_court).replace("{SEQ}", str(count).zfill(3))
    return matricule


def _get_parents(db, id_eleve):
    return (
        db.query(ParentTuteur, EleveParent.tuteur_legal)
        .join(EleveParent, EleveParent.id_parent == ParentTuteur.id)
        .filter(EleveParent.id_eleve == id_eleve)
        .all()
    )


def _serialize_inscription(db, inscription):
    data = InscriptionSchema().dump(inscription)
    classe = db.query(Classe).filter(Classe.id == inscription.id_classe).first()
    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == inscription.id_annee).first()
    data["classe_nom"] = classe.libelle if classe else None
    data["annee_libelle"] = annee.libelle if annee else None
    return data


def _serialize_eleve_list_item(db, eleve, id_annee=None):
    result = EleveSchema().dump(eleve)
    inscr_q = db.query(Inscription).filter(Inscription.id_eleve == eleve.id)
    if id_annee:
        inscr_q = inscr_q.filter(Inscription.id_annee == id_annee)
    inscr = inscr_q.order_by(Inscription.date_inscription.desc()).first()
    if inscr:
        classe = db.query(Classe).filter(Classe.id == inscr.id_classe).first()
        result["statut"] = inscr.statut
        result["est_boursier"] = inscr.est_boursier
        result["id_classe"] = str(inscr.id_classe)
        result["id_annee"] = str(inscr.id_annee)
        result["classe_nom"] = classe.libelle if classe else None
        if classe:
            niveau = db.query(NiveauEtude).filter(NiveauEtude.id == classe.id_niveau).first()
            if niveau:
                result["niveau_libelle"] = niveau.libelle
                result["cycle"] = niveau.cycle
    return result


@blp.route("/")
class ElevesList(MethodView):
    @jwt_required()
    @require_role(
        "administrateur", "directeur", "secretariat", "enseignant", "agent_comptable", "parent"
    )
    def get(self):
        db = get_db()
        user = get_current_user()
        q = db.query(Eleve)
        statut = request.args.get("statut")
        id_classe = request.args.get("id_classe")
        id_annee = request.args.get("id_annee")
        search = request.args.get("q", "").strip()
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 15)), 1), 100)

        if statut == "boursier" or id_classe or (statut and statut != "boursier") or id_annee:
            q = q.join(Inscription)
            if id_annee:
                q = q.filter(Inscription.id_annee == uuid.UUID(id_annee))
            if id_classe:
                q = q.filter(Inscription.id_classe == uuid.UUID(id_classe))
            if statut == "boursier":
                q = q.filter(Inscription.est_boursier.is_(True))
            elif statut:
                q = q.filter(Inscription.statut == statut)

        if search:
            like = f"%{search}%"
            q = q.filter(
                or_(
                    Eleve.nom.ilike(like),
                    Eleve.prenom.ilike(like),
                    Eleve.matricule.ilike(like),
                )
            )

        q = filter_eleves_by_role(q, user)
        total = q.count()
        eleves = (
            q.order_by(Eleve.nom, Eleve.prenom)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        annee_uuid = uuid.UUID(id_annee) if id_annee else None
        if not annee_uuid:
            active = db.query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
            annee_uuid = active.id if active else None

        return jsonify({
            "items": [_serialize_eleve_list_item(db, e, annee_uuid) for e in eleves],
            "total": total,
            "page": page,
            "per_page": per_page,
        })

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(EleveCreateSchema)
    @blp.response(201, EleveDetailSchema)
    def post(self, data):
        db = get_db()
        matricule = _generer_matricule(db, data["id_annee"])

        eleve = Eleve(
            id=uuid.uuid4(),
            matricule=matricule,
            nom=data["nom"],
            prenom=data["prenom"],
            sexe=data.get("sexe"),
            date_naissance=data.get("date_naissance"),
            lieu_naissance=data.get("lieu_naissance"),
            adresse=data.get("adresse"),
        )
        if data.get("notes_medicales"):
            eleve.notes_medicales_chiffrees = chiffrer_notes_medicales(data["notes_medicales"])

        db.add(eleve)

        inscription = Inscription(
            id=uuid.uuid4(),
            id_eleve=eleve.id,
            id_classe=data["id_classe"],
            id_annee=data["id_annee"],
        )
        db.add(inscription)

        for p_data in data.get("parents", []):
            tuteur_legal = p_data.pop("tuteur_legal", False)
            parent = ParentTuteur(id=uuid.uuid4(), **p_data)
            db.add(parent)
            db.flush()
            link = EleveParent(id_eleve=eleve.id, id_parent=parent.id, tuteur_legal=tuteur_legal)
            db.add(link)

        db.commit()
        log_audit("CREATION_ELEVE", get_current_user().id, "eleve", eleve.id)
        return eleve, 201


@blp.route("/<uuid:id_eleve>")
class EleveDetail(MethodView):
    @jwt_required()
    @require_role(
        "administrateur", "directeur", "secretariat", "enseignant", "agent_comptable", "parent"
    )
    def get(self, id_eleve):
        db = get_db()
        user = get_current_user()
        if user.role == "parent" and not parent_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403

        eleve = db.query(Eleve).filter(Eleve.id == id_eleve).first()
        if not eleve:
            return jsonify({"message": "Élève introuvable"}), 404

        result = EleveSchema().dump(eleve)
        if eleve.photo_url:
            result["photo_url"] = f"/api/eleves/{id_eleve}/photo"
        if can_view_medical_notes(user) and eleve.notes_medicales_chiffrees:
            result["notes_medicales"] = dechiffrer_notes_medicales(eleve.notes_medicales_chiffrees)

        parents = []
        for parent, tuteur_legal in _get_parents(db, id_eleve):
            p = ParentTuteurSchema().dump(parent)
            p["tuteur_legal"] = tuteur_legal
            parents.append(p)
        result["parents"] = parents

        active = db.query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
        if active:
            inscr = (
                db.query(Inscription)
                .filter(Inscription.id_eleve == id_eleve, Inscription.id_annee == active.id)
                .first()
            )
            if inscr:
                classe = db.query(Classe).filter(Classe.id == inscr.id_classe).first()
                result["statut"] = inscr.statut
                result["est_boursier"] = inscr.est_boursier
                result["classe_nom"] = classe.libelle if classe else None

        return result

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(EleveSchema)
    @blp.response(200, EleveSchema)
    def put(self, data, id_eleve):
        db = get_db()
        eleve = db.query(Eleve).filter(Eleve.id == id_eleve).first()
        if not eleve:
            return jsonify({"message": "Élève introuvable"}), 404
        notes_med = request.json.get("notes_medicales") if request.json else None
        for key, value in data.items():
            if key != "matricule":
                setattr(eleve, key, value)
        if notes_med is not None:
            eleve.notes_medicales_chiffrees = (
                chiffrer_notes_medicales(notes_med) if notes_med else None
            )
        db.commit()
        return eleve


@blp.route("/<uuid:id_eleve>/inscriptions")
class InscriptionsEleve(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "parent")
    def get(self, id_eleve):
        db = get_db()
        user = get_current_user()
        if user.role == "parent" and not parent_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403
        inscriptions = db.query(Inscription).filter(Inscription.id_eleve == id_eleve).all()
        return jsonify([_serialize_inscription(db, i) for i in inscriptions])

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(InscriptionCreateSchema)
    @blp.response(201, InscriptionSchema)
    def post(self, data, id_eleve):
        db = get_db()
        existing = (
            db.query(Inscription)
            .filter(
                Inscription.id_eleve == id_eleve,
                Inscription.id_annee == data["id_annee"],
            )
            .first()
        )
        if existing:
            return jsonify({"message": "Une inscription existe déjà pour cette année scolaire"}), 409

        inscription = Inscription(id=uuid.uuid4(), id_eleve=id_eleve, **data)
        db.add(inscription)
        db.commit()
        return _serialize_inscription(db, inscription), 201


@blp.route("/inscriptions/<uuid:id_inscription>/statut")
class InscriptionStatut(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def patch(self, id_inscription):
        db = get_db()
        inscription = db.query(Inscription).filter(Inscription.id == id_inscription).first()
        if not inscription:
            return jsonify({"message": "Inscription introuvable"}), 404
        statut = request.json.get("statut")
        if statut not in ("inscrit", "abandon", "suspendu", "reinscrit", "diplome"):
            return jsonify({"message": "Statut invalide"}), 400
        inscription.statut = statut
        inscription.date_statut_maj = date.today()
        db.commit()
        return _serialize_inscription(db, inscription)


@blp.route("/<uuid:id_eleve>/upload")
class EleveUpload(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def post(self, id_eleve):
        db = get_db()
        eleve = db.query(Eleve).filter(Eleve.id == id_eleve).first()
        if not eleve:
            return jsonify({"message": "Élève introuvable"}), 404

        if "file" not in request.files:
            return jsonify({"message": "Fichier requis"}), 400

        file = request.files["file"]
        doc_type = request.form.get("type", "autre")
        upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "eleves", str(id_eleve))
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        pieces = list(eleve.pieces_justificatives or [])
        pieces.append({"type": doc_type, "url": filepath, "date_upload": date.today().isoformat()})
        eleve.pieces_justificatives = pieces
        db.commit()
        return jsonify({"message": "Fichier uploadé", "url": filepath}), 201


@blp.route("/<uuid:id_eleve>/photo")
class ElevePhoto(MethodView):
    @jwt_required()
    @require_role(
        "administrateur", "directeur", "secretariat", "enseignant", "agent_comptable", "parent"
    )
    def get(self, id_eleve):
        db = get_db()
        user = get_current_user()
        if user.role == "parent" and not parent_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403
        eleve = db.query(Eleve).filter(Eleve.id == id_eleve).first()
        if not eleve or not eleve.photo_url or not os.path.isfile(eleve.photo_url):
            return jsonify({"message": "Photo introuvable"}), 404
        return send_file(eleve.photo_url)

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def post(self, id_eleve):
        db = get_db()
        eleve = db.query(Eleve).filter(Eleve.id == id_eleve).first()
        if not eleve:
            return jsonify({"message": "Élève introuvable"}), 404
        if "file" not in request.files:
            return jsonify({"message": "Fichier requis"}), 400
        file = request.files["file"]
        upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "eleves", str(id_eleve), "photo")
        os.makedirs(upload_dir, exist_ok=True)
        ext = os.path.splitext(secure_filename(file.filename))[1] or ".jpg"
        filepath = os.path.join(upload_dir, f"photo{ext}")
        file.save(filepath)
        eleve.photo_url = filepath
        db.commit()
        return jsonify({"message": "Photo enregistrée", "photo_url": f"/api/eleves/{id_eleve}/photo"}), 201
