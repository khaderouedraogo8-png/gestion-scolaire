"""Module 8 — Tableau de bord BI (direction / secrétariat / comptable / enseignant)."""
import uuid
from datetime import date, timedelta

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from sqlalchemy import func, text

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import (
    get_enseignant_for_user,
    get_teacher_class_ids,
    require_role,
)
from app.extensions import get_db
from app.models import Absence, AffectationEnseignant, Evaluation, Inscription, Paiement
from app.services.classes_navigation import get_absences_par_classe_dashboard
from app.services.tenant import get_current_school_id, tenant_query

blp = Blueprint("dashboard", __name__, url_prefix="/dashboard", description="Tableau de bord")

_STAFF_DASH = ("administrateur", "directeur", "agent_comptable", "secretariat")
_TEACHER_DASH = ("enseignant",)


@blp.route("/stats")
class DashboardStats(MethodView):
    @jwt_required()
    @require_role(*_STAFF_DASH)
    def get(self):
        db = get_db()
        user = get_current_user()
        id_annee = request.args.get("id_annee")
        school_id = get_current_school_id()
        role = user.role

        effectifs_query = db.execute(
            text("""
                SELECT ne.libelle AS niveau, e.sexe, COUNT(DISTINCT i.id_eleve) AS effectif
                FROM inscription i
                JOIN eleve e ON e.id = i.id_eleve
                JOIN classe c ON c.id = i.id_classe
                JOIN niveau_etude ne ON ne.id = c.id_niveau
                WHERE i.statut IN ('inscrit', 'reinscrit')
                  AND i.school_id = CAST(:school_id AS UUID)
                  AND (:id_annee IS NULL OR i.id_annee = CAST(:id_annee AS UUID))
                GROUP BY ne.libelle, ne.ordre, e.sexe
                ORDER BY ne.ordre, e.sexe
            """),
            {"id_annee": id_annee, "school_id": str(school_id)},
        ).fetchall()

        effectifs = [
            {"niveau": r[0], "sexe": r[1], "effectif": r[2]} for r in effectifs_query
        ]

        # Taux de réussite depuis academic_subject_result (rules engine),
        # seuil = 50% de scale_max (fallback 20 → 10).
        taux_reussite = []
        include_academic = role in ("administrateur", "directeur", "secretariat")
        if include_academic:
            try:
                reussite_query = db.execute(
                    text("""
                        SELECT mat.libelle,
                               COUNT(*) AS total,
                               COUNT(*) FILTER (
                                 WHERE r.moyenne IS NOT NULL
                                   AND r.moyenne >= (COALESCE(r.scale_max, 20) / 2.0)
                               ) AS reussis
                        FROM academic_subject_result r
                        JOIN matiere mat ON mat.id = r.id_matiere
                        WHERE r.school_id = CAST(:school_id AS UUID)
                          AND r.incomplete = false
                          AND r.is_stale = false
                        GROUP BY mat.libelle
                        ORDER BY mat.libelle
                    """),
                    {"school_id": str(school_id)},
                ).fetchall()

                taux_reussite = [
                    {
                        "matiere": r[0],
                        "total": r[1],
                        "reussis": r[2],
                        "taux": round(r[2] / r[1] * 100, 1) if r[1] > 0 else 0,
                    }
                    for r in reussite_query
                ]
            except Exception:
                db.rollback()
                taux_reussite = []
                school_id = get_current_school_id()

        tresorerie = 0
        total_du = 0
        include_finance = role in ("administrateur", "directeur", "agent_comptable")
        if include_finance and id_annee:
            paiements = (
                tenant_query(Paiement)
                .with_entities(func.coalesce(func.sum(Paiement.montant_verse), 0))
                .filter(Paiement.id_annee == id_annee, Paiement.annule.is_(False))
                .scalar()
            )
            tresorerie = float(paiements or 0)

            du = db.execute(
                text("""
                    SELECT COALESCE(SUM(ec.montant), 0)
                    FROM inscription i
                    JOIN classe c ON c.id = i.id_classe
                    JOIN frais_scolaire fs ON fs.id_niveau = c.id_niveau AND fs.id_annee = i.id_annee
                    JOIN echeance_paiement ec ON ec.id_frais = fs.id
                    WHERE i.id_annee = CAST(:id_annee AS UUID)
                      AND i.school_id = CAST(:school_id AS UUID)
                      AND i.statut IN ('inscrit', 'reinscrit')
                """),
                {"id_annee": id_annee, "school_id": str(school_id)},
            ).scalar()
            total_du = float(du or 0)

        taux_recouvrement = round(tresorerie / total_du * 100, 1) if total_du > 0 else 0

        inscrits_q = tenant_query(Inscription).with_entities(func.count(Inscription.id)).filter(
            Inscription.statut.in_(("inscrit", "reinscrit"))
        )
        if id_annee:
            inscrits_q = inscrits_q.filter(Inscription.id_annee == id_annee)
        total_eleves = inscrits_q.scalar()

        absences_mois = tenant_query(Absence).with_entities(func.count(Absence.id)).scalar() or 0

        # Classes / enseignants (direction)
        total_classes = 0
        total_enseignants = 0
        if role in ("administrateur", "directeur", "secretariat") and id_annee:
            from app.models import Classe, Enseignant

            total_classes = (
                tenant_query(Classe)
                .filter(Classe.id_annee == uuid.UUID(id_annee))
                .count()
            )
            total_enseignants = tenant_query(Enseignant).count()

        # Bulletins publiés (direction)
        bulletins_publies = 0
        if include_academic:
            from app.models import Bulletin

            bulletins_publies = (
                tenant_query(Bulletin).filter(Bulletin.statut == "publie").count()
            )

        payload = {
            "role_view": role,
            "effectifs_par_niveau": effectifs if include_academic or role == "secretariat" else [],
            "taux_reussite_par_matiere": taux_reussite,
            "tresorerie": tresorerie if include_finance else None,
            "total_du": total_du if include_finance else None,
            "taux_recouvrement": taux_recouvrement if include_finance else None,
            "total_eleves_inscrits": total_eleves,
            "total_absences": absences_mois if role != "agent_comptable" else None,
            "total_classes": total_classes or None,
            "total_enseignants": total_enseignants or None,
            "bulletins_publies": bulletins_publies if include_academic else None,
        }
        return jsonify(payload)


@blp.route("/enseignant")
class DashboardEnseignant(MethodView):
    """Dashboard enseignant — uniquement classes / matières / évaluations affectées."""

    @jwt_required()
    @require_role(*_TEACHER_DASH)
    def get(self):
        db = get_db()
        user = get_current_user()
        enseignant = get_enseignant_for_user(user)
        if not enseignant:
            return jsonify({
                "classes": [],
                "matieres": [],
                "evaluations_ouvertes": [],
                "total_absences_7j": 0,
                "eleves_suivis": 0,
            })

        class_ids = get_teacher_class_ids(user)
        id_annee = request.args.get("id_annee")

        affectations = (
            db.query(AffectationEnseignant)
            .filter(AffectationEnseignant.id_enseignant == enseignant.id)
            .all()
        )
        matieres = []
        seen_mat = set()
        classes = []
        seen_cls = set()
        from app.models import Classe, Matiere

        for aff in affectations:
            if aff.id_classe not in seen_cls:
                classe = (
                    tenant_query(Classe).filter(Classe.id == aff.id_classe).first()
                )
                if classe:
                    classes.append({
                        "id": str(classe.id),
                        "libelle": classe.libelle,
                    })
                    seen_cls.add(aff.id_classe)
            if aff.id_matiere not in seen_mat:
                mat = tenant_query(Matiere).filter(Matiere.id == aff.id_matiere).first()
                if mat:
                    matieres.append({"id": str(mat.id), "libelle": mat.libelle})
                    seen_mat.add(aff.id_matiere)

        evals_q = tenant_query(Evaluation).filter(
            Evaluation.id_enseignant == enseignant.id,
            Evaluation.statut_saisie.in_(("ouverte", "brouillon", "en_cours")),
        )
        if class_ids:
            evals_q = evals_q.filter(Evaluation.id_classe.in_(class_ids))
        evaluations = [
            {
                "id": str(e.id),
                "libelle": getattr(e, "libelle", None) or e.type_evaluation,
                "type_evaluation": e.type_evaluation,
                "id_classe": str(e.id_classe),
                "statut": e.statut_saisie,
            }
            for e in evals_q.order_by(Evaluation.date_evaluation.desc()).limit(20).all()
        ]

        since = date.today() - timedelta(days=7)
        abs_q = tenant_query(Absence).filter(Absence.date_absence >= since)
        if class_ids:
            # Absence n'a pas id_classe — périmètre via inscriptions des classes affectées
            eleves_classes = (
                db.query(Inscription.id_eleve)
                .filter(
                    Inscription.school_id == enseignant.school_id,
                    Inscription.id_classe.in_(class_ids),
                    Inscription.statut.in_(("inscrit", "reinscrit")),
                )
                .distinct()
            )
            abs_q = abs_q.filter(Absence.id_eleve.in_(eleves_classes))
        total_abs = abs_q.count()

        eleves_suivis = 0
        if class_ids:
            iq = tenant_query(Inscription).filter(
                Inscription.id_classe.in_(class_ids),
                Inscription.statut.in_(("inscrit", "reinscrit")),
            )
            if id_annee:
                iq = iq.filter(Inscription.id_annee == uuid.UUID(id_annee))
            eleves_suivis = iq.with_entities(
                func.count(func.distinct(Inscription.id_eleve))
            ).scalar() or 0

        return jsonify({
            "classes": classes,
            "matieres": matieres,
            "evaluations_ouvertes": evaluations,
            "total_absences_7j": total_abs,
            "eleves_suivis": eleves_suivis,
        })


@blp.route("/absences-par-classe")
class DashboardAbsencesParClasse(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable", "secretariat", "enseignant")
    def get(self):
        user = get_current_user()
        # Comptable : pas d'indicateur absences dans son espace finance
        if user.role == "agent_comptable":
            return jsonify({"absences_jour": [], "non_justifiees_en_attente": []})
        db = get_db()
        id_annee = request.args.get("id_annee")
        jours = int(request.args.get("jours_non_justifiees", 7))
        annee_uuid = uuid.UUID(id_annee) if id_annee else None
        data = get_absences_par_classe_dashboard(
            db, id_annee=annee_uuid, jours_non_justifiees=jours
        )
        # Enseignant : filtrer aux classes affectées
        if user.role == "enseignant":
            allowed = {str(cid) for cid in get_teacher_class_ids(user)}

            def _filter_cycles(cycles):
                out = []
                for block in cycles or []:
                    classes = [
                        c for c in block.get("classes", [])
                        if str(c.get("id_classe")) in allowed
                    ]
                    if classes:
                        out.append({
                            **block,
                            "classes": classes,
                            "total": sum(c.get("count", 0) for c in classes),
                        })
                return out

            data = {
                "absences_jour": _filter_cycles(data.get("absences_jour")),
                "non_justifiees_en_attente": _filter_cycles(
                    data.get("non_justifiees_en_attente")
                ),
            }
        return jsonify(data)


@blp.route("/parent-evolution")
class DashboardParentEvolution(MethodView):
    """Évolution simple parent : moyenne par période + absences par période (données réelles)."""

    @jwt_required()
    @require_role("parent")
    def get(self):
        from app.auth.permissions import get_parent_eleve_ids, parent_has_eleve_access
        from app.models import Bulletin, Eleve, Trimestre

        db = get_db()
        user = get_current_user()
        id_eleve_raw = request.args.get("id_eleve")
        eleve_ids = get_parent_eleve_ids(user)
        if not eleve_ids:
            return jsonify({"enfants": []})

        if id_eleve_raw:
            eid = uuid.UUID(id_eleve_raw)
            if not parent_has_eleve_access(user, eid):
                return jsonify({"message": "Accès refusé"}), 403
            target_ids = [eid]
        else:
            target_ids = list(eleve_ids)

        enfants = []
        for eid in target_ids:
            eleve = tenant_query(Eleve).filter(Eleve.id == eid).first()
            if not eleve:
                continue

            # Moyennes depuis bulletins publiés (pas de calcul parallèle)
            bulletins = (
                tenant_query(Bulletin)
                .filter(Bulletin.id_eleve == eid, Bulletin.statut == "publie")
                .all()
            )
            moyennes = []
            for b in bulletins:
                trim = db.query(Trimestre).filter(Trimestre.id == b.id_trimestre).first()
                moyennes.append({
                    "id_period": str(b.id_trimestre),
                    "periode": trim.label if trim else str(b.id_trimestre),
                    "moyenne_generale": float(b.moyenne_generale) if b.moyenne_generale is not None else None,
                })

            # Absences groupées par trimestre (période) via chevauchement de dates
            absences = tenant_query(Absence).filter(Absence.id_eleve == eid).all()
            by_period: dict[str, int] = {}
            trimestres = (
                db.query(Trimestre)
                .filter(Trimestre.school_id == get_current_school_id())
                .all()
            )
            for a in absences:
                matched = None
                for t in trimestres:
                    if t.date_debut <= a.date_absence <= t.date_fin:
                        matched = t
                        break
                key = matched.label if matched else "hors_periode"
                by_period[key] = by_period.get(key, 0) + 1

            enfants.append({
                "id_eleve": str(eid),
                "nom": eleve.nom,
                "prenom": eleve.prenom,
                "moyennes_par_periode": moyennes,
                "absences_par_periode": [
                    {"periode": k, "count": v} for k, v in sorted(by_period.items())
                ],
                "total_absences": len(absences),
            })

        return jsonify({"enfants": enfants})
