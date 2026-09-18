"""E-learning LMS — devoirs, remises, quiz (scoring), ressources, progression."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import (
    ElearningDevoir,
    ElearningQuiz,
    ElearningQuizTentative,
    ElearningRemise,
    ElearningRessource,
    Eleve,
)
from app.services.elearning_scoring import score_quiz, strip_answers_for_student
from app.services.tenant import (
    apply_tenant_school,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)

blp = Blueprint("elearning", __name__, description="E-learning LMS")

STAFF = ("administrateur", "directeur", "enseignant", "secretariat")
READERS = (*STAFF, "parent", "eleve")
WRITERS = ("administrateur", "directeur", "enseignant")


def _eleve_for_user(user):
    if user.role != "eleve":
        return None
    return tenant_query(Eleve).filter(Eleve.id_utilisateur == user.id).first()


def _is_staff(user) -> bool:
    return user.role in STAFF or user.role == "administrateur"


class DevoirSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_classe = fields.UUID(allow_none=True)
    id_matiere = fields.UUID(allow_none=True)
    titre = fields.String(required=True)
    consignes = fields.String(allow_none=True)
    date_limite = fields.DateTime(allow_none=True)
    note_max = fields.Decimal(as_string=True, load_default="20")
    pieces_jointes = fields.Raw(allow_none=True)
    cree_par = fields.UUID(dump_only=True, allow_none=True)
    publie = fields.Boolean(load_default=True)
    created_at = fields.DateTime(dump_only=True)


class RemiseSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_devoir = fields.UUID(required=True)
    id_eleve = fields.UUID(allow_none=True)
    fichier_url = fields.String(allow_none=True)
    contenu = fields.String(allow_none=True)
    date_remise = fields.DateTime(dump_only=True)
    note = fields.Decimal(as_string=True, allow_none=True)
    commentaire = fields.String(allow_none=True)
    statut = fields.String(dump_only=True)
    notee_par = fields.UUID(dump_only=True, allow_none=True)
    notee_le = fields.DateTime(dump_only=True, allow_none=True)


class RemiseNoteSchema(Schema):
    note = fields.Decimal(as_string=True, required=True)
    commentaire = fields.String(allow_none=True)


class QuizSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_classe = fields.UUID(allow_none=True)
    id_matiere = fields.UUID(allow_none=True)
    titre = fields.String(required=True)
    questions = fields.Raw(allow_none=True)
    duree_minutes = fields.Integer(allow_none=True)
    note_max = fields.Decimal(as_string=True, load_default="20")
    tentatives_max = fields.Integer(load_default=3)
    afficher_correction = fields.Boolean(load_default=True)
    publie = fields.Boolean(load_default=False)
    cree_par = fields.UUID(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class QuizTentativeSubmitSchema(Schema):
    id_eleve = fields.UUID(allow_none=True)
    reponses = fields.Raw(required=True)


class TentativeSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_quiz = fields.UUID()
    id_eleve = fields.UUID()
    score_brut = fields.Decimal(as_string=True, allow_none=True)
    score_max = fields.Decimal(as_string=True, allow_none=True)
    note = fields.Decimal(as_string=True, allow_none=True)
    detail_correction = fields.Raw(allow_none=True)
    started_at = fields.DateTime(dump_only=True)
    finished_at = fields.DateTime(dump_only=True, allow_none=True)


class RessourceSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_classe = fields.UUID(allow_none=True)
    id_matiere = fields.UUID(allow_none=True)
    titre = fields.String(required=True)
    type_ressource = fields.String(load_default="lien")
    url = fields.String(allow_none=True)
    description = fields.String(allow_none=True)
    publie = fields.Boolean(load_default=True)
    cree_par = fields.UUID(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


# ---------------------------------------------------------------------------
# Devoirs
# ---------------------------------------------------------------------------


@blp.route("/devoirs")
class DevoirsResource(MethodView):
    @jwt_required()
    @require_role(*READERS)
    def get(self):
        user = get_current_user()
        q = tenant_query(ElearningDevoir)
        id_classe = request.args.get("id_classe")
        if id_classe:
            q = q.filter(ElearningDevoir.id_classe == uuid.UUID(id_classe))
        if user.role in ("eleve", "parent"):
            q = q.filter(ElearningDevoir.publie.is_(True))
        return jsonify(
            DevoirSchema(many=True).dump(q.order_by(ElearningDevoir.created_at.desc()).all())
        )

    @jwt_required()
    @require_role(*WRITERS)
    @blp.arguments(DevoirSchema)
    @blp.response(201, DevoirSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        if "note_max" in data and data["note_max"] is not None:
            data["note_max"] = Decimal(str(data["note_max"]))
        row = ElearningDevoir(id=uuid.uuid4(), cree_par=user.id, **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/devoirs/<uuid:id_devoir>")
class DevoirDetail(MethodView):
    @jwt_required()
    @require_role(*READERS)
    def get(self, id_devoir):
        row = get_or_404_tenant(ElearningDevoir, id_devoir)
        user = get_current_user()
        if user.role in ("eleve", "parent") and not row.publie:
            abort(404, message="Devoir introuvable")
        return jsonify(DevoirSchema().dump(row))

    @jwt_required()
    @require_role(*WRITERS)
    @blp.arguments(DevoirSchema(partial=True))
    def put(self, data, id_devoir):
        db = get_db()
        row = get_or_404_tenant(ElearningDevoir, id_devoir)
        if "note_max" in data and data["note_max"] is not None:
            data["note_max"] = Decimal(str(data["note_max"]))
        for k, v in data.items():
            setattr(row, k, v)
        db.commit()
        return jsonify(DevoirSchema().dump(row))

    @jwt_required()
    @require_role(*WRITERS)
    def delete(self, id_devoir):
        db = get_db()
        row = get_or_404_tenant(ElearningDevoir, id_devoir)
        db.delete(row)
        db.commit()
        return jsonify({"message": "Devoir supprimé"})


@blp.route("/devoirs/<uuid:id_devoir>/stats")
class DevoirStats(MethodView):
    @jwt_required()
    @require_role(*STAFF)
    def get(self, id_devoir):
        devoir = get_or_404_tenant(ElearningDevoir, id_devoir)
        remises = (
            tenant_query(ElearningRemise)
            .filter(ElearningRemise.id_devoir == id_devoir)
            .all()
        )
        notes = [r.note for r in remises if r.note is not None]
        avg = float(sum(notes) / len(notes)) if notes else None
        return jsonify(
            {
                "id_devoir": str(devoir.id),
                "titre": devoir.titre,
                "note_max": str(devoir.note_max),
                "nb_remises": len(remises),
                "nb_notees": len(notes),
                "moyenne": round(avg, 2) if avg is not None else None,
                "en_attente": sum(1 for r in remises if r.note is None),
            }
        )


# ---------------------------------------------------------------------------
# Remises
# ---------------------------------------------------------------------------


@blp.route("/remises")
class RemisesResource(MethodView):
    @jwt_required()
    @require_role(*READERS)
    def get(self):
        user = get_current_user()
        q = tenant_query(ElearningRemise)
        id_devoir = request.args.get("id_devoir")
        id_eleve = request.args.get("id_eleve")
        if id_devoir:
            q = q.filter(ElearningRemise.id_devoir == uuid.UUID(id_devoir))
        if id_eleve:
            q = q.filter(ElearningRemise.id_eleve == uuid.UUID(id_eleve))
        linked = _eleve_for_user(user)
        if linked:
            q = q.filter(ElearningRemise.id_eleve == linked.id)
        return jsonify(RemiseSchema(many=True).dump(q.all()))

    @jwt_required()
    @require_role(*READERS)
    @blp.arguments(RemiseSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        get_or_404_tenant(ElearningDevoir, data["id_devoir"])

        linked = _eleve_for_user(user)
        id_eleve = data.get("id_eleve")
        if linked:
            id_eleve = linked.id
        elif not id_eleve:
            abort(400, message="id_eleve requis")
        else:
            get_or_404_tenant(Eleve, id_eleve)

        if user.role == "eleve" and not linked:
            abort(403, message="Compte élève non lié")

        existing = (
            tenant_query(ElearningRemise)
            .filter(
                ElearningRemise.id_devoir == data["id_devoir"],
                ElearningRemise.id_eleve == id_eleve,
            )
            .first()
        )
        payload = {
            k: v
            for k, v in data.items()
            if k not in ("id_devoir", "id_eleve", "note", "commentaire")
        }
        if existing:
            if linked and existing.note is not None:
                abort(409, message="Remise déjà notée — modification interdite")
            for k, v in payload.items():
                setattr(existing, k, v)
            existing.date_remise = datetime.now(UTC)
            existing.statut = "remise"
            db.commit()
            return jsonify(RemiseSchema().dump(existing)), 200

        row = ElearningRemise(
            id=uuid.uuid4(),
            id_devoir=data["id_devoir"],
            id_eleve=id_eleve,
            statut="remise",
            **payload,
        )
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return jsonify(RemiseSchema().dump(row)), 201


@blp.route("/remises/<uuid:id_remise>")
class RemiseDetail(MethodView):
    @jwt_required()
    @require_role(*WRITERS)
    @blp.arguments(RemiseNoteSchema)
    def put(self, data, id_remise):
        """Noter / commenter une remise."""
        db = get_db()
        user = get_current_user()
        row = get_or_404_tenant(ElearningRemise, id_remise)
        row.note = Decimal(str(data["note"]))
        if "commentaire" in data:
            row.commentaire = data["commentaire"]
        row.statut = "note"
        row.notee_par = user.id
        row.notee_le = datetime.now(UTC)
        db.commit()
        return jsonify(RemiseSchema().dump(row))


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------


@blp.route("/quiz")
class QuizResource(MethodView):
    @jwt_required()
    @require_role(*READERS)
    def get(self):
        user = get_current_user()
        q = tenant_query(ElearningQuiz)
        id_classe = request.args.get("id_classe")
        if id_classe:
            q = q.filter(ElearningQuiz.id_classe == uuid.UUID(id_classe))
        if user.role in ("eleve", "parent"):
            q = q.filter(ElearningQuiz.publie.is_(True))
        rows = q.order_by(ElearningQuiz.created_at.desc()).all()
        dumped = QuizSchema(many=True).dump(rows)
        if user.role in ("eleve", "parent"):
            for item, row in zip(dumped, rows, strict=True):
                item["questions"] = strip_answers_for_student(row.questions)
                item["nb_questions"] = len(item["questions"])
        return jsonify(dumped)

    @jwt_required()
    @require_role(*WRITERS)
    @blp.arguments(QuizSchema)
    @blp.response(201, QuizSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        if "note_max" in data and data["note_max"] is not None:
            data["note_max"] = Decimal(str(data["note_max"]))
        row = ElearningQuiz(id=uuid.uuid4(), cree_par=user.id, **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/quiz/<uuid:id_quiz>")
class QuizDetail(MethodView):
    @jwt_required()
    @require_role(*READERS)
    def get(self, id_quiz):
        row = get_or_404_tenant(ElearningQuiz, id_quiz)
        user = get_current_user()
        if user.role in ("eleve", "parent") and not row.publie:
            abort(404, message="Quiz introuvable")
        data = QuizSchema().dump(row)
        if user.role in ("eleve", "parent"):
            data["questions"] = strip_answers_for_student(row.questions)
        return jsonify(data)

    @jwt_required()
    @require_role(*WRITERS)
    @blp.arguments(QuizSchema(partial=True))
    def put(self, data, id_quiz):
        db = get_db()
        row = get_or_404_tenant(ElearningQuiz, id_quiz)
        if "note_max" in data and data["note_max"] is not None:
            data["note_max"] = Decimal(str(data["note_max"]))
        for k, v in data.items():
            setattr(row, k, v)
        db.commit()
        return jsonify(QuizSchema().dump(row))

    @jwt_required()
    @require_role(*WRITERS)
    def delete(self, id_quiz):
        db = get_db()
        row = get_or_404_tenant(ElearningQuiz, id_quiz)
        db.delete(row)
        db.commit()
        return jsonify({"message": "Quiz supprimé"})


@blp.route("/quiz/<uuid:id_quiz>/passer")
class QuizPasser(MethodView):
    @jwt_required()
    @require_role(*READERS)
    @blp.arguments(QuizTentativeSubmitSchema)
    def post(self, data, id_quiz):
        """Soumettre une tentative — correction automatique."""
        db = get_db()
        user = get_current_user()
        quiz = get_or_404_tenant(ElearningQuiz, id_quiz)
        if not quiz.publie and user.role in ("eleve", "parent"):
            abort(404, message="Quiz introuvable")

        linked = _eleve_for_user(user)
        id_eleve = data.get("id_eleve")
        if linked:
            id_eleve = linked.id
        elif not id_eleve:
            abort(400, message="id_eleve requis")
        else:
            get_or_404_tenant(Eleve, id_eleve)

        nb = (
            tenant_query(ElearningQuizTentative)
            .filter(
                ElearningQuizTentative.id_quiz == id_quiz,
                ElearningQuizTentative.id_eleve == id_eleve,
            )
            .count()
        )
        if nb >= (quiz.tentatives_max or 3):
            abort(409, message=f"Nombre max de tentatives atteint ({quiz.tentatives_max})")

        result = score_quiz(quiz.questions, data["reponses"], note_max=quiz.note_max or 20)
        detail = result["detail"] if quiz.afficher_correction else None
        if user.role in ("eleve", "parent") and not quiz.afficher_correction:
            detail = [{"index": d["index"], "correct": d["correct"], "points": d["points"]} for d in result["detail"]]

        row = ElearningQuizTentative(
            id=uuid.uuid4(),
            id_quiz=id_quiz,
            id_eleve=id_eleve,
            reponses=data["reponses"],
            score_brut=result["score_brut"],
            score_max=result["score_max"],
            note=result["note"],
            detail_correction=detail,
            finished_at=datetime.now(UTC),
        )
        apply_tenant_school(row)
        db.add(row)
        db.commit()

        payload = TentativeSchema().dump(row)
        payload["nb_correctes"] = result["nb_correctes"]
        payload["nb_questions"] = result["nb_questions"]
        payload["tentative_numero"] = nb + 1
        payload["tentatives_restantes"] = max(0, (quiz.tentatives_max or 3) - (nb + 1))
        return jsonify(payload), 201


@blp.route("/quiz/<uuid:id_quiz>/tentatives")
class QuizTentativesList(MethodView):
    @jwt_required()
    @require_role(*READERS)
    def get(self, id_quiz):
        get_or_404_tenant(ElearningQuiz, id_quiz)
        user = get_current_user()
        q = tenant_query(ElearningQuizTentative).filter(
            ElearningQuizTentative.id_quiz == id_quiz
        )
        linked = _eleve_for_user(user)
        id_eleve = request.args.get("id_eleve")
        if linked:
            q = q.filter(ElearningQuizTentative.id_eleve == linked.id)
        elif id_eleve:
            q = q.filter(ElearningQuizTentative.id_eleve == uuid.UUID(id_eleve))
        elif user.role not in STAFF and user.role != "administrateur":
            abort(403, message="Filtre id_eleve requis")
        rows = q.order_by(ElearningQuizTentative.started_at.desc()).all()
        return jsonify(TentativeSchema(many=True).dump(rows))


# ---------------------------------------------------------------------------
# Ressources
# ---------------------------------------------------------------------------


@blp.route("/ressources")
class RessourcesResource(MethodView):
    @jwt_required()
    @require_role(*READERS)
    def get(self):
        user = get_current_user()
        q = tenant_query(ElearningRessource)
        id_classe = request.args.get("id_classe")
        if id_classe:
            q = q.filter(ElearningRessource.id_classe == uuid.UUID(id_classe))
        if user.role in ("eleve", "parent"):
            q = q.filter(ElearningRessource.publie.is_(True))
        return jsonify(
            RessourceSchema(many=True).dump(
                q.order_by(ElearningRessource.created_at.desc()).all()
            )
        )

    @jwt_required()
    @require_role(*WRITERS)
    @blp.arguments(RessourceSchema)
    @blp.response(201, RessourceSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        url = data.get("url")
        if url and not str(url).startswith(("https://", "http://", "/")):
            abort(400, message="URL ressource invalide (http/https ou chemin local)")
        row = ElearningRessource(id=uuid.uuid4(), cree_par=user.id, **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/ressources/<uuid:id_ressource>")
class RessourceDetail(MethodView):
    @jwt_required()
    @require_role(*WRITERS)
    @blp.arguments(RessourceSchema(partial=True))
    def put(self, data, id_ressource):
        db = get_db()
        row = get_or_404_tenant(ElearningRessource, id_ressource)
        if data.get("url"):
            url = str(data["url"])
            if not url.startswith(("https://", "http://", "/")):
                abort(400, message="URL ressource invalide")
        for k, v in data.items():
            setattr(row, k, v)
        db.commit()
        return jsonify(RessourceSchema().dump(row))

    @jwt_required()
    @require_role(*WRITERS)
    def delete(self, id_ressource):
        db = get_db()
        row = get_or_404_tenant(ElearningRessource, id_ressource)
        db.delete(row)
        db.commit()
        return jsonify({"message": "Ressource supprimée"})


# ---------------------------------------------------------------------------
# Progression classe
# ---------------------------------------------------------------------------


@blp.route("/progression")
class ProgressionClasse(MethodView):
    @jwt_required()
    @require_role(*STAFF)
    def get(self):
        """Synthèse remises + quiz pour une classe."""
        id_classe = request.args.get("id_classe")
        if not id_classe:
            abort(400, message="id_classe requis")
        cid = uuid.UUID(id_classe)
        devoirs = (
            tenant_query(ElearningDevoir)
            .filter(ElearningDevoir.id_classe == cid, ElearningDevoir.publie.is_(True))
            .all()
        )
        quizs = (
            tenant_query(ElearningQuiz)
            .filter(ElearningQuiz.id_classe == cid, ElearningQuiz.publie.is_(True))
            .all()
        )
        ressources = (
            tenant_query(ElearningRessource)
            .filter(ElearningRessource.id_classe == cid, ElearningRessource.publie.is_(True))
            .count()
        )
        devoir_ids = [d.id for d in devoirs]
        remises_count = 0
        if devoir_ids:
            remises_count = (
                tenant_query(ElearningRemise)
                .filter(ElearningRemise.id_devoir.in_(devoir_ids))
                .count()
            )
        quiz_ids = [q.id for q in quizs]
        tentatives_count = 0
        if quiz_ids:
            tentatives_count = (
                tenant_query(ElearningQuizTentative)
                .filter(ElearningQuizTentative.id_quiz.in_(quiz_ids))
                .count()
            )
        return jsonify(
            {
                "id_classe": str(cid),
                "nb_devoirs": len(devoirs),
                "nb_quiz": len(quizs),
                "nb_ressources": ressources,
                "nb_remises": remises_count,
                "nb_tentatives_quiz": tentatives_count,
            }
        )
