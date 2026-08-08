"""Routes programme pédagogique : devoirs récurrents et PDFs de classe."""
import uuid
from datetime import date

from flask import jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import (
    parent_has_classe_access,
    require_role,
    teacher_has_class_access,
    teacher_has_matiere_classe_access,
)
from app.extensions import get_db
from app.models import Classe, Enseignant, Inscription, Matiere, ProgrammeDevoir, SeanceCours
from app.schemas.pedagogie import (
    ProgrammeDevoirSchema,
    ProgrammeDevoirUpdateSchema,
    SeanceCoursSchema,
)
from app.services.calendrier_scolaire import date_est_bloquee, id_annee_pour_classe, notifier_parents_classe
from app.services.charge_travail import stats_charge_classe
from app.services.generation_pedagogique import (
    JOURS,
    generer_pdf_calendrier_compositions,
    generer_pdf_fiche_appel,
    generer_pdf_fiche_correction,
    generer_pdf_fiche_scolarite,
    generer_pdf_liste_eleves,
    generer_pdf_programme_devoirs,
    generer_pdf_programme_trimestriel,
)

blp = Blueprint("pedagogie", __name__, url_prefix="/pedagogie", description="Programme pédagogique")


def _serialize_programme(db, row):
    data = ProgrammeDevoirSchema().dump(row)
    matiere = db.query(Matiere).filter(Matiere.id == row.id_matiere).first()
    data["matiere_nom"] = matiere.libelle if matiere else None
    data["jour_libelle"] = JOURS.get(row.jour_semaine, str(row.jour_semaine))
    return data


def _can_edit_programme(user, id_classe, id_matiere=None):
    if user.role in ("administrateur", "directeur", "secretariat"):
        return True
    if user.role == "enseignant":
        if id_matiere:
            return teacher_has_matiere_classe_access(user, id_classe, id_matiere)
        return teacher_has_class_access(user, id_classe)
    return False


def _notify_programme_change(db, id_classe: uuid.UUID, message: str):
    classe = db.query(Classe).filter(Classe.id == id_classe).first()
    libelle = classe.libelle if classe else "votre classe"
    notifier_parents_classe(
        db,
        id_classe,
        "programme_devoirs_modifie",
        f"Le programme des devoirs de {libelle} a été mis à jour : {message}",
    )


def _serialize_seance(db, row):
    data = SeanceCoursSchema().dump(row)
    matiere = db.query(Matiere).filter(Matiere.id == row.id_matiere).first()
    enseignant = db.query(Enseignant).filter(Enseignant.id == row.id_enseignant).first()
    data["matiere_nom"] = matiere.libelle if matiere else None
    data["enseignant_nom"] = f"{enseignant.prenom} {enseignant.nom}" if enseignant else None
    return data


@blp.route("/programme-devoirs")
class ProgrammeDevoirsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self):
        db = get_db()
        user = get_current_user()
        id_classe = request.args.get("id_classe")
        id_annee = request.args.get("id_annee")
        if not id_classe or not id_annee:
            return jsonify({"message": "id_classe et id_annee requis"}), 400
        classe_uuid = uuid.UUID(id_classe)
        annee_uuid = uuid.UUID(id_annee)
        if user.role == "parent" and not parent_has_classe_access(user, classe_uuid, annee_uuid):
            return jsonify({"message": "Accès refusé"}), 403
        rows = (
            db.query(ProgrammeDevoir)
            .filter(
                ProgrammeDevoir.id_classe == classe_uuid,
                ProgrammeDevoir.id_annee == annee_uuid,
            )
            .order_by(ProgrammeDevoir.jour_semaine)
            .all()
        )
        return jsonify([_serialize_programme(db, r) for r in rows])

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.arguments(ProgrammeDevoirSchema)
    def post(self, data):
        user = get_current_user()
        if not _can_edit_programme(user, data["id_classe"], data["id_matiere"]):
            return jsonify({"message": "Accès refusé"}), 403
        db = get_db()
        existing = (
            db.query(ProgrammeDevoir)
            .filter(
                ProgrammeDevoir.id_classe == data["id_classe"],
                ProgrammeDevoir.id_matiere == data["id_matiere"],
                ProgrammeDevoir.jour_semaine == data["jour_semaine"],
                ProgrammeDevoir.id_annee == data["id_annee"],
            )
            .first()
        )
        if existing:
            existing.frequence = data.get("frequence", "hebdomadaire")
            existing.note = data.get("note")
            db.commit()
            _notify_programme_change(db, data["id_classe"], "entrée modifiée")
            return jsonify(_serialize_programme(db, existing)), 200
        row = ProgrammeDevoir(id=uuid.uuid4(), **data)
        db.add(row)
        db.commit()
        _notify_programme_change(db, data["id_classe"], "nouvelle entrée ajoutée")
        return jsonify(_serialize_programme(db, row)), 201


@blp.route("/programme-devoirs/<uuid:id_programme>")
class ProgrammeDevoirDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.arguments(ProgrammeDevoirUpdateSchema)
    def put(self, data, id_programme):
        user = get_current_user()
        db = get_db()
        row = db.query(ProgrammeDevoir).filter(ProgrammeDevoir.id == id_programme).first()
        if not row:
            return jsonify({"message": "Entrée introuvable"}), 404
        if not _can_edit_programme(user, row.id_classe, row.id_matiere):
            return jsonify({"message": "Accès refusé"}), 403
        for key, value in data.items():
            setattr(row, key, value)
        db.commit()
        _notify_programme_change(db, row.id_classe, "entrée modifiée")
        return jsonify(_serialize_programme(db, row))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def delete(self, id_programme):
        user = get_current_user()
        db = get_db()
        row = db.query(ProgrammeDevoir).filter(ProgrammeDevoir.id == id_programme).first()
        if not row:
            return jsonify({"message": "Entrée introuvable"}), 404
        if not _can_edit_programme(user, row.id_classe, row.id_matiere):
            return jsonify({"message": "Accès refusé"}), 403
        id_classe = row.id_classe
        db.delete(row)
        db.commit()
        _notify_programme_change(db, id_classe, "entrée supprimée")
        return jsonify({"message": "Supprimé"})


@blp.route("/pdf/programme-devoirs")
class PdfProgrammeDevoirs(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self):
        id_classe = request.args.get("id_classe")
        id_annee = request.args.get("id_annee")
        if not id_classe or not id_annee:
            return jsonify({"message": "id_classe et id_annee requis"}), 400
        user = get_current_user()
        classe_uuid = uuid.UUID(id_classe)
        annee_uuid = uuid.UUID(id_annee)
        if user.role == "parent" and not parent_has_classe_access(user, classe_uuid, annee_uuid):
            return jsonify({"message": "Accès refusé"}), 403
        try:
            path = generer_pdf_programme_devoirs(classe_uuid, annee_uuid)
            classe = get_db().query(Classe).filter(Classe.id == classe_uuid).first()
            name = f"programme_devoirs_{classe.libelle if classe else id_classe}.pdf"
            return send_file(path, mimetype="application/pdf", as_attachment=False, download_name=name)
        except RuntimeError as e:
            return jsonify({"message": str(e)}), 503


@blp.route("/pdf/calendrier-compositions")
class PdfCalendrierCompositions(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self):
        id_classe = request.args.get("id_classe")
        id_trimestre = request.args.get("id_trimestre")
        if not id_classe or not id_trimestre:
            return jsonify({"message": "id_classe et id_trimestre requis"}), 400
        user = get_current_user()
        include_brouillon = user.role in ("administrateur", "directeur", "secretariat", "enseignant")
        try:
            path = generer_pdf_calendrier_compositions(
                uuid.UUID(id_classe), uuid.UUID(id_trimestre), include_brouillon=include_brouillon
            )
            return send_file(path, mimetype="application/pdf", as_attachment=False, download_name="calendrier_compositions.pdf")
        except RuntimeError as e:
            return jsonify({"message": str(e)}), 503


@blp.route("/pdf/liste-eleves")
class PdfListeEleves(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        id_classe = request.args.get("id_classe")
        if not id_classe:
            return jsonify({"message": "id_classe requis"}), 400
        try:
            path = generer_pdf_liste_eleves(uuid.UUID(id_classe))
            return send_file(path, mimetype="application/pdf", as_attachment=False, download_name="liste_eleves.pdf")
        except RuntimeError as e:
            return jsonify({"message": str(e)}), 503


@blp.route("/pdf/fiche-correction")
class PdfFicheCorrection(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    def get(self):
        id_evaluation = request.args.get("id_evaluation")
        if not id_evaluation:
            return jsonify({"message": "id_evaluation requis"}), 400
        try:
            path = generer_pdf_fiche_correction(uuid.UUID(id_evaluation))
            return send_file(path, mimetype="application/pdf", as_attachment=False, download_name="fiche_correction.pdf")
        except ValueError as e:
            return jsonify({"message": str(e)}), 404
        except RuntimeError as e:
            return jsonify({"message": str(e)}), 503


@blp.route("/pdf/fiche-appel")
class PdfFicheAppel(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        id_classe = request.args.get("id_classe")
        date_str = request.args.get("date")
        if not id_classe:
            return jsonify({"message": "id_classe requis"}), 400
        date_appel = date.fromisoformat(date_str) if date_str else None
        try:
            path = generer_pdf_fiche_appel(uuid.UUID(id_classe), date_appel)
            return send_file(path, mimetype="application/pdf", as_attachment=False, download_name="fiche_appel.pdf")
        except RuntimeError as e:
            return jsonify({"message": str(e)}), 503


@blp.route("/pdf/fiche-scolarite")
class PdfFicheScolarite(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "agent_comptable", "enseignant")
    def get(self):
        id_classe = request.args.get("id_classe")
        id_annee = request.args.get("id_annee")
        if not id_classe or not id_annee:
            return jsonify({"message": "id_classe et id_annee requis"}), 400
        try:
            path = generer_pdf_fiche_scolarite(uuid.UUID(id_classe), uuid.UUID(id_annee))
            return send_file(path, mimetype="application/pdf", as_attachment=False, download_name="fiche_scolarite.pdf")
        except RuntimeError as e:
            return jsonify({"message": str(e)}), 503


@blp.route("/charge-travail")
class ChargeTravailResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        id_classe = request.args.get("id_classe")
        id_annee = request.args.get("id_annee")
        id_trimestre = request.args.get("id_trimestre")
        if not id_classe or not id_annee:
            return jsonify({"message": "id_classe et id_annee requis"}), 400
        db = get_db()
        stats = stats_charge_classe(
            db,
            uuid.UUID(id_classe),
            uuid.UUID(id_annee),
            uuid.UUID(id_trimestre) if id_trimestre else None,
        )
        return jsonify(stats)


@blp.route("/seances")
class SeancesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self):
        db = get_db()
        user = get_current_user()
        id_classe = request.args.get("id_classe")
        id_annee = request.args.get("id_annee")
        if not id_classe or not id_annee:
            return jsonify({"message": "id_classe et id_annee requis"}), 400
        classe_uuid = uuid.UUID(id_classe)
        annee_uuid = uuid.UUID(id_annee)
        if user.role == "parent" and not parent_has_classe_access(user, classe_uuid, annee_uuid):
            return jsonify({"message": "Accès refusé"}), 403
        rows = (
            db.query(SeanceCours)
            .filter(SeanceCours.id_classe == classe_uuid, SeanceCours.id_annee == annee_uuid)
            .order_by(SeanceCours.date_seance.desc())
            .all()
        )
        return jsonify([_serialize_seance(db, r) for r in rows])

    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    @blp.arguments(SeanceCoursSchema)
    def post(self, data):
        user = get_current_user()
        if not _can_edit_programme(user, data["id_classe"], data["id_matiere"]):
            return jsonify({"message": "Accès refusé"}), 403
        db = get_db()
        bloque, libelle = date_est_bloquee(db, data["id_annee"], data["date_seance"])
        if bloque:
            return jsonify({"message": f"Date bloquée : {libelle}"}), 400
        existing = (
            db.query(SeanceCours)
            .filter(
                SeanceCours.id_classe == data["id_classe"],
                SeanceCours.id_matiere == data["id_matiere"],
                SeanceCours.date_seance == data["date_seance"],
            )
            .first()
        )
        if existing:
            existing.contenu = data["contenu"]
            existing.id_enseignant = data["id_enseignant"]
            db.commit()
            return jsonify(_serialize_seance(db, existing)), 200
        row = SeanceCours(id=uuid.uuid4(), **data)
        db.add(row)
        db.commit()
        return jsonify(_serialize_seance(db, row)), 201


@blp.route("/seances/<uuid:id_seance>")
class SeanceDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    @blp.arguments(SeanceCoursSchema)
    def put(self, data, id_seance):
        user = get_current_user()
        db = get_db()
        row = db.query(SeanceCours).filter(SeanceCours.id == id_seance).first()
        if not row:
            return jsonify({"message": "Séance introuvable"}), 404
        if not _can_edit_programme(user, row.id_classe, row.id_matiere):
            return jsonify({"message": "Accès refusé"}), 403
        bloque, libelle = date_est_bloquee(db, data["id_annee"], data["date_seance"])
        if bloque:
            return jsonify({"message": f"Date bloquée : {libelle}"}), 400
        for key, value in data.items():
            setattr(row, key, value)
        db.commit()
        return jsonify(_serialize_seance(db, row))

    @jwt_required()
    @require_role("administrateur", "directeur", "enseignant")
    def delete(self, id_seance):
        user = get_current_user()
        db = get_db()
        row = db.query(SeanceCours).filter(SeanceCours.id == id_seance).first()
        if not row:
            return jsonify({"message": "Séance introuvable"}), 404
        if not _can_edit_programme(user, row.id_classe, row.id_matiere):
            return jsonify({"message": "Accès refusé"}), 403
        db.delete(row)
        db.commit()
        return jsonify({"message": "Supprimé"})


@blp.route("/pdf/programme-trimestriel")
class PdfProgrammeTrimestriel(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self):
        id_classe = request.args.get("id_classe")
        id_trimestre = request.args.get("id_trimestre")
        id_annee = request.args.get("id_annee")
        if not id_classe or not id_trimestre or not id_annee:
            return jsonify({"message": "id_classe, id_trimestre et id_annee requis"}), 400
        user = get_current_user()
        classe_uuid = uuid.UUID(id_classe)
        annee_uuid = uuid.UUID(id_annee)
        if user.role == "parent" and not parent_has_classe_access(user, classe_uuid, annee_uuid):
            return jsonify({"message": "Accès refusé"}), 403
        try:
            path = generer_pdf_programme_trimestriel(
                classe_uuid, uuid.UUID(id_trimestre), annee_uuid
            )
            return send_file(
                path,
                mimetype="application/pdf",
                as_attachment=False,
                download_name="programme_trimestriel.pdf",
            )
        except RuntimeError as e:
            return jsonify({"message": str(e)}), 503
