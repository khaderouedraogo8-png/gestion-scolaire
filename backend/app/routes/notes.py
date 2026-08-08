"""Module 2 — Routes évaluations, notes, bulletins."""
import uuid
from datetime import UTC

from flask import jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import (
    get_enseignant_for_user,
    get_parent_classe_ids,
    get_parent_eleve_ids,
    parent_has_eleve_access,
    require_role,
    teacher_has_matiere_classe_access,
)
from app.extensions import get_db
from app.models import (
    Bulletin,
    Classe,
    CoefficientMatiere,
    Eleve,
    Enseignant,
    Evaluation,
    Inscription,
    Matiere,
    NiveauEtude,
    Note,
    Trimestre,
)
from app.schemas.notes import (
    BulletinSchema,
    CoefficientMatiereSchema,
    EvaluationCreateSchema,
    EvaluationSchema,
    MatiereSchema,
    NoteBatchSchema,
)
from app.services.calcul_moyennes import refresh_moyenne_matiere_view
from app.services.calendrier_scolaire import date_est_bloquee, id_annee_pour_trimestre
from app.services.envoi_notification import creer_notification
from app.services.generation_bulletin import (
    generer_bulletin,
    generer_bulletin_pdf,
    publier_bulletin,
    valider_bulletin,
)
from app.utils.audit_logger import log_audit

blp = Blueprint("notes", __name__, url_prefix="/notes", description="Notes et bulletins")


def _serialize_evaluation(db, evaluation):
    data = EvaluationSchema().dump(evaluation)
    matiere = db.query(Matiere).filter(Matiere.id == evaluation.id_matiere).first()
    classe = db.query(Classe).filter(Classe.id == evaluation.id_classe).first()
    trimestre = db.query(Trimestre).filter(Trimestre.id == evaluation.id_trimestre).first()
    data["matiere_nom"] = matiere.libelle if matiere else None
    data["classe_nom"] = classe.libelle if classe else None
    data["trimestre_numero"] = trimestre.numero if trimestre else None
    data["statut_publication"] = evaluation.statut_publication
    data["statut_saisie"] = evaluation.statut_saisie
    return data


def _serialize_bulletin(db, bulletin):
    data = BulletinSchema().dump(bulletin)
    eleve = db.query(Eleve).filter(Eleve.id == bulletin.id_eleve).first()
    trimestre = db.query(Trimestre).filter(Trimestre.id == bulletin.id_trimestre).first()
    data["prenom"] = eleve.prenom if eleve else None
    data["nom"] = eleve.nom if eleve else None
    data["matricule"] = eleve.matricule if eleve else None
    data["trimestre"] = trimestre.numero if trimestre else None
    data["moyenne"] = float(bulletin.moyenne_generale) if bulletin.moyenne_generale is not None else None
    if eleve and trimestre:
        ins = (
            db.query(Inscription)
            .filter(
                Inscription.id_eleve == eleve.id,
                Inscription.id_annee == trimestre.id_annee,
            )
            .first()
        )
        if ins:
            classe = db.query(Classe).filter(Classe.id == ins.id_classe).first()
            data["classe_nom"] = classe.libelle if classe else None
            data["id_classe"] = str(ins.id_classe)
    return data


def _default_enseignant_id(db):
    enseignant = db.query(Enseignant).first()
    if not enseignant:
        raise ValueError("Aucun enseignant enregistré — ajoutez un enseignant d'abord")
    return enseignant.id


@blp.route("/matieres")
class MatieresResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.response(200, MatiereSchema(many=True))
    def get(self):
        db = get_db()
        return db.query(Matiere).order_by(Matiere.libelle).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(MatiereSchema)
    @blp.response(201, MatiereSchema)
    def post(self, data):
        db = get_db()
        matiere = Matiere(id=uuid.uuid4(), **data)
        db.add(matiere)
        db.commit()
        return matiere, 201


@blp.route("/matieres/<uuid:id_matiere>")
class MatiereDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(MatiereSchema)
    @blp.response(200, MatiereSchema)
    def put(self, data, id_matiere):
        db = get_db()
        matiere = db.query(Matiere).filter(Matiere.id == id_matiere).first()
        if not matiere:
            return jsonify({"message": "Matière introuvable"}), 404
        matiere.libelle = data["libelle"]
        matiere.code = data.get("code")
        db.commit()
        return matiere

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_matiere):
        db = get_db()
        matiere = db.query(Matiere).filter(Matiere.id == id_matiere).first()
        if not matiere:
            return jsonify({"message": "Matière introuvable"}), 404
        db.delete(matiere)
        db.commit()
        return jsonify({"message": "Matière supprimée"}), 200


@blp.route("/coefficients")
class CoefficientsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        db = get_db()
        q = db.query(CoefficientMatiere)
        id_niveau = request.args.get("id_niveau")
        if id_niveau:
            q = q.filter(CoefficientMatiere.id_niveau == uuid.UUID(id_niveau))
        rows = q.all()
        result = []
        for c in rows:
            data = CoefficientMatiereSchema().dump(c)
            matiere = db.query(Matiere).filter(Matiere.id == c.id_matiere).first()
            niveau = db.query(NiveauEtude).filter(NiveauEtude.id == c.id_niveau).first()
            data["matiere_libelle"] = matiere.libelle if matiere else None
            data["niveau_libelle"] = niveau.libelle if niveau else None
            result.append(data)
        return jsonify(result)

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(CoefficientMatiereSchema)
    def post(self, data):
        db = get_db()
        existing = (
            db.query(CoefficientMatiere)
            .filter(
                CoefficientMatiere.id_matiere == data["id_matiere"],
                CoefficientMatiere.id_niveau == data["id_niveau"],
            )
            .first()
        )
        if existing:
            existing.coefficient = data["coefficient"]
            db.commit()
            return CoefficientMatiereSchema().dump(existing), 200
        coef = CoefficientMatiere(id=uuid.uuid4(), **data)
        db.add(coef)
        db.commit()
        return CoefficientMatiereSchema().dump(coef), 201


@blp.route("/coefficients/<uuid:id_coefficient>")
class CoefficientDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_coefficient):
        db = get_db()
        coef = db.query(CoefficientMatiere).filter(CoefficientMatiere.id == id_coefficient).first()
        if not coef:
            return jsonify({"message": "Coefficient introuvable"}), 404
        db.delete(coef)
        db.commit()
        return jsonify({"message": "Coefficient supprimé"}), 200


@blp.route("/evaluations")
class EvaluationsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant", "parent")
    def get(self):
        db = get_db()
        user = get_current_user()
        q = db.query(Evaluation)
        id_classe = request.args.get("id_classe")
        id_trimestre = request.args.get("id_trimestre")
        type_evaluation = request.args.get("type_evaluation")
        if id_classe:
            q = q.filter(Evaluation.id_classe == uuid.UUID(id_classe))
        if id_trimestre:
            q = q.filter(Evaluation.id_trimestre == uuid.UUID(id_trimestre))
        if type_evaluation:
            q = q.filter(Evaluation.type_evaluation == type_evaluation)
        if user.role == "enseignant":
            enseignant = get_enseignant_for_user(user)
            if enseignant:
                q = q.filter(Evaluation.id_enseignant == enseignant.id)
        elif user.role == "parent":
            classe_ids = get_parent_classe_ids(user)
            if not classe_ids:
                return jsonify([])
            q = q.filter(Evaluation.id_classe.in_(classe_ids))
            q = q.filter(
                (Evaluation.type_evaluation != "examen")
                | (Evaluation.statut_publication == "publie")
            )
            q = q.filter(Evaluation.statut_saisie == "cloturee")
        evaluations = q.order_by(Evaluation.date_evaluation.desc()).all()
        return jsonify([_serialize_evaluation(db, e) for e in evaluations])

    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    @blp.arguments(EvaluationCreateSchema)
    @blp.response(201, EvaluationSchema)
    def post(self, data):
        user = get_current_user()
        db = get_db()

        if user.role == "enseignant":
            enseignant = get_enseignant_for_user(user)
            if not enseignant or not teacher_has_matiere_classe_access(
                user, data["id_classe"], data["id_matiere"]
            ):
                return jsonify({"message": "Accès refusé à cette classe/matière"}), 403
            data["id_enseignant"] = enseignant.id
        elif not data.get("id_enseignant"):
            try:
                data["id_enseignant"] = _default_enseignant_id(db)
            except ValueError as e:
                return jsonify({"message": str(e)}), 400

        id_annee = id_annee_pour_trimestre(db, data["id_trimestre"])
        if id_annee:
            bloque, libelle = date_est_bloquee(db, id_annee, data["date_evaluation"])
            if bloque:
                return jsonify({"message": f"Date bloquée par le calendrier scolaire : {libelle}"}), 400

        evaluation = Evaluation(
            id=uuid.uuid4(),
            statut_publication="brouillon" if data["type_evaluation"] == "examen" else "publie",
            statut_saisie="en_cours",
            **data,
        )
        db.add(evaluation)
        db.commit()
        return evaluation, 201


@blp.route("/evaluations/<uuid:id_evaluation>")
class EvaluationDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    def get(self, id_evaluation):
        db = get_db()
        evaluation = db.query(Evaluation).filter(Evaluation.id == id_evaluation).first()
        if not evaluation:
            return jsonify({"message": "Évaluation introuvable"}), 404
        return jsonify(_serialize_evaluation(db, evaluation))


@blp.route("/evaluations/<uuid:id_evaluation>/publier")
class PublierEvaluation(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    def post(self, id_evaluation):
        db = get_db()
        user = get_current_user()
        evaluation = db.query(Evaluation).filter(Evaluation.id == id_evaluation).first()
        if not evaluation:
            return jsonify({"message": "Évaluation introuvable"}), 404
        if evaluation.type_evaluation != "examen":
            return jsonify({"message": "Seules les compositions peuvent être publiées"}), 400
        if user.role == "enseignant" and not teacher_has_matiere_classe_access(
            user, evaluation.id_classe, evaluation.id_matiere
        ):
            return jsonify({"message": "Accès refusé"}), 403
        evaluation.statut_publication = "publie"
        db.commit()
        log_audit("PUBLICATION_COMPOSITION", user.id, "evaluation", evaluation.id)
        inscriptions = (
            db.query(Inscription)
            .filter(
                Inscription.id_classe == evaluation.id_classe,
                Inscription.statut.in_(("inscrit", "reinscrit")),
            )
            .all()
        )
        matiere = db.query(Matiere).filter(Matiere.id == evaluation.id_matiere).first()
        libelle = evaluation.libelle or "Composition"
        mat_nom = matiere.libelle if matiere else "—"
        for ins in inscriptions:
            creer_notification(
                "sms",
                "composition_publiee",
                f"Composition programmée : {libelle} ({mat_nom}) le {evaluation.date_evaluation.strftime('%d/%m/%Y')}.",
                id_eleve=ins.id_eleve,
            )
        return jsonify(_serialize_evaluation(db, evaluation))


@blp.route("/evaluations/<uuid:id_evaluation>/cloturer")
class CloturerEvaluation(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    def post(self, id_evaluation):
        db = get_db()
        user = get_current_user()
        evaluation = db.query(Evaluation).filter(Evaluation.id == id_evaluation).first()
        if not evaluation:
            return jsonify({"message": "Évaluation introuvable"}), 404
        if user.role == "enseignant" and not teacher_has_matiere_classe_access(
            user, evaluation.id_classe, evaluation.id_matiere
        ):
            return jsonify({"message": "Accès refusé"}), 403
        evaluation.statut_saisie = "cloturee"
        db.commit()
        log_audit("CLOTURE_EVALUATION", user.id, "evaluation", evaluation.id)
        inscriptions = (
            db.query(Inscription)
            .filter(
                Inscription.id_classe == evaluation.id_classe,
                Inscription.statut.in_(("inscrit", "reinscrit")),
            )
            .all()
        )
        matiere = db.query(Matiere).filter(Matiere.id == evaluation.id_matiere).first()
        libelle = evaluation.libelle or evaluation.type_evaluation
        mat_nom = matiere.libelle if matiere else "—"
        for ins in inscriptions:
            creer_notification(
                "sms",
                "notes_publiees",
                f"Notes publiées pour {libelle} ({mat_nom}). Consultez l'espace parent.",
                id_eleve=ins.id_eleve,
            )
        return jsonify(_serialize_evaluation(db, evaluation))


@blp.route("/evaluations/<uuid:id_evaluation>/rouvrir")
class RouvrirEvaluation(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    def post(self, id_evaluation):
        db = get_db()
        user = get_current_user()
        evaluation = db.query(Evaluation).filter(Evaluation.id == id_evaluation).first()
        if not evaluation:
            return jsonify({"message": "Évaluation introuvable"}), 404
        if user.role == "enseignant" and not teacher_has_matiere_classe_access(
            user, evaluation.id_classe, evaluation.id_matiere
        ):
            return jsonify({"message": "Accès refusé"}), 403
        evaluation.statut_saisie = "en_cours"
        db.commit()
        log_audit("REOUVERTURE_EVALUATION", user.id, "evaluation", evaluation.id)
        return jsonify(_serialize_evaluation(db, evaluation))


@blp.route("/evaluations/<uuid:id_evaluation>/notes")
class NotesEvaluation(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant", "parent")
    def get(self, id_evaluation):
        db = get_db()
        user = get_current_user()
        evaluation = db.query(Evaluation).filter(Evaluation.id == id_evaluation).first()
        if not evaluation:
            return jsonify({"message": "Évaluation introuvable"}), 404

        if user.role == "parent":
            if evaluation.statut_saisie != "cloturee":
                return jsonify({"message": "Notes non publiées"}), 403
            if evaluation.type_evaluation == "examen" and evaluation.statut_publication != "publie":
                return jsonify({"message": "Composition non publiée"}), 403
            eleve_ids = get_parent_eleve_ids(user)
            inscriptions = (
                db.query(Inscription)
                .filter(
                    Inscription.id_classe == evaluation.id_classe,
                    Inscription.id_eleve.in_(eleve_ids),
                    Inscription.statut.in_(("inscrit", "reinscrit")),
                )
                .all()
            )
        else:
            inscriptions = (
                db.query(Inscription)
                .filter(
                    Inscription.id_classe == evaluation.id_classe,
                    Inscription.statut.in_(("inscrit", "reinscrit")),
                )
                .all()
            )
        notes_map = {
            n.id_eleve: n
            for n in db.query(Note).filter(Note.id_evaluation == id_evaluation).all()
        }

        grid = []
        for ins in inscriptions:
            eleve = db.query(Eleve).filter(Eleve.id == ins.id_eleve).first()
            if not eleve:
                continue
            note = notes_map.get(eleve.id)
            grid.append({
                "id_eleve": str(eleve.id),
                "nom": eleve.nom,
                "prenom": eleve.prenom,
                "matricule": eleve.matricule,
                "valeur_note": float(note.valeur_note) if note and note.valeur_note is not None else None,
                "absent": note.absent if note else False,
                "appreciation": note.appreciation if note else "",
                "note_id": str(note.id) if note else None,
            })

        return jsonify({
            "evaluation": _serialize_evaluation(db, evaluation),
            "notes": grid,
        })

    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    @blp.arguments(NoteBatchSchema)
    def post(self, data, id_evaluation):
        db = get_db()
        user = get_current_user()
        evaluation = db.query(Evaluation).filter(Evaluation.id == id_evaluation).first()
        if not evaluation:
            return jsonify({"message": "Évaluation introuvable"}), 404

        if user.role == "enseignant" and not teacher_has_matiere_classe_access(
            user, evaluation.id_classe, evaluation.id_matiere
        ):
            return jsonify({"message": "Accès refusé"}), 403

        for note_data in data["notes"]:
            id_eleve = note_data["id_eleve"]
            existing = (
                db.query(Note)
                .filter(Note.id_evaluation == id_evaluation, Note.id_eleve == id_eleve)
                .first()
            )
            if existing:
                from datetime import datetime

                if note_data.get("absent"):
                    existing.absent = True
                    existing.valeur_note = None
                else:
                    existing.absent = False
                    existing.valeur_note = note_data.get("valeur_note")
                existing.modifie_par = user.id
                existing.modifie_le = datetime.now(UTC)
                existing.appreciation = note_data.get("appreciation")
                log_audit("MODIFICATION_NOTE", user.id, "note", existing.id)
            else:
                note = Note(
                    id=uuid.uuid4(),
                    id_evaluation=id_evaluation,
                    id_eleve=id_eleve,
                    valeur_note=None if note_data.get("absent") else note_data.get("valeur_note"),
                    absent=note_data.get("absent", False),
                    appreciation=note_data.get("appreciation"),
                    saisi_par=user.id,
                )
                db.add(note)

        db.commit()
        refresh_moyenne_matiere_view(db)
        return jsonify({"message": "Notes enregistrées"}), 200


@blp.route("/bulletins")
class BulletinsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self):
        db = get_db()
        user = get_current_user()
        q = db.query(Bulletin)
        id_eleve = request.args.get("id_eleve")
        id_trimestre = request.args.get("id_trimestre")
        id_classe = request.args.get("id_classe")
        trimestre_num = request.args.get("trimestre")

        if user.role == "parent":
            eleve_ids = get_parent_eleve_ids(user)
            if not eleve_ids:
                return jsonify({"items": [], "total": 0})
            q = q.filter(Bulletin.id_eleve.in_(eleve_ids), Bulletin.statut == "publie")

        if id_eleve:
            eid = uuid.UUID(id_eleve)
            if user.role == "parent" and not parent_has_eleve_access(user, eid):
                return jsonify({"message": "Accès refusé"}), 403
            q = q.filter(Bulletin.id_eleve == eid)
        if id_trimestre:
            q = q.filter(Bulletin.id_trimestre == uuid.UUID(id_trimestre))
        elif trimestre_num:
            trimestres = db.query(Trimestre).filter(Trimestre.numero == int(trimestre_num)).all()
            if trimestres:
                q = q.filter(Bulletin.id_trimestre.in_([t.id for t in trimestres]))

        bulletins = q.order_by(Bulletin.date_generation.desc()).all()
        items = [_serialize_bulletin(db, b) for b in bulletins]

        if id_classe:
            items = [b for b in items if b.get("id_classe") == id_classe]

        return jsonify({"items": items, "total": len(items)})


@blp.route("/bulletins/generer")
class GenererBulletin(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    def post(self):
        data = request.json or {}
        user = get_current_user()

        # Génération par classe
        if data.get("id_classe") and data.get("id_trimestre"):
            db = get_db()
            id_classe = uuid.UUID(str(data["id_classe"]))
            id_trimestre = uuid.UUID(str(data["id_trimestre"]))
            inscriptions = (
                db.query(Inscription)
                .filter(
                    Inscription.id_classe == id_classe,
                    Inscription.statut.in_(("inscrit", "reinscrit")),
                )
                .all()
            )
            created = []
            errors = []
            for ins in inscriptions:
                try:
                    b = generer_bulletin(ins.id_eleve, id_trimestre, user.id)
                    created.append(_serialize_bulletin(db, b))
                except ValueError as e:
                    errors.append({"id_eleve": str(ins.id_eleve), "message": str(e)})
            return jsonify({"items": created, "errors": errors, "total": len(created)}), 201

        # Génération individuelle
        id_eleve = uuid.UUID(data["id_eleve"])
        id_trimestre = uuid.UUID(data["id_trimestre"])
        try:
            bulletin = generer_bulletin(id_eleve, id_trimestre, user.id)
            db = get_db()
            return _serialize_bulletin(db, bulletin), 201
        except ValueError as e:
            return jsonify({"message": str(e)}), 400


@blp.route("/bulletins/<uuid:id_bulletin>/valider")
class ValiderBulletin(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def post(self, id_bulletin):
        user = get_current_user()
        db = get_db()
        try:
            bulletin = valider_bulletin(id_bulletin, user.id)
            return _serialize_bulletin(db, bulletin)
        except ValueError as e:
            return jsonify({"message": str(e)}), 400


@blp.route("/bulletins/<uuid:id_bulletin>/publier")
class PublierBulletin(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def post(self, id_bulletin):
        user = get_current_user()
        db = get_db()
        try:
            bulletin = publier_bulletin(id_bulletin, user.id)
            return _serialize_bulletin(db, bulletin)
        except ValueError as e:
            return jsonify({"message": str(e)}), 400


@blp.route("/bulletins/<uuid:id_bulletin>")
class BulletinDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    def patch(self, id_bulletin):
        db = get_db()
        bulletin = db.query(Bulletin).filter(Bulletin.id == id_bulletin).first()
        if not bulletin:
            return jsonify({"message": "Bulletin introuvable"}), 404
        if bulletin.statut == "publie":
            return jsonify({"message": "Bulletin publié — lecture seule"}), 400
        appreciation = (request.json or {}).get("appreciation_generale")
        if appreciation is not None:
            bulletin.appreciation_generale = appreciation
            db.commit()
        return _serialize_bulletin(db, bulletin)


@blp.route("/bulletins/<uuid:id_bulletin>/pdf")
class BulletinPDF(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "parent")
    def get(self, id_bulletin):
        db = get_db()
        user = get_current_user()
        bulletin = db.query(Bulletin).filter(Bulletin.id == id_bulletin).first()
        if not bulletin:
            return jsonify({"message": "Bulletin introuvable"}), 404
        if user.role == "parent":
            if not parent_has_eleve_access(user, bulletin.id_eleve):
                return jsonify({"message": "Accès refusé"}), 403
            if bulletin.statut != "publie":
                return jsonify({"message": "Bulletin non publié"}), 403
        try:
            path = generer_bulletin_pdf(bulletin)
            eleve = db.query(Eleve).filter(Eleve.id == bulletin.id_eleve).first()
            name = f"bulletin_{eleve.matricule if eleve else id_bulletin}.pdf"
            return send_file(path, mimetype="application/pdf", as_attachment=False, download_name=name)
        except ValueError as e:
            return jsonify({"message": str(e)}), 400
