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
        id_annee = request.args.get("id_annee") or None
        if id_annee == "":
            id_annee = None
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


@blp.route("/comptable")
class DashboardComptable(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable")
    def get(self):
        """Vue comptable : encaissements jour, impayés, échéances 7j, MM pending."""
        from datetime import datetime

        from app.models import AnneeScolaire, EcheancePaiement, FraisScolaire
        from app.services.finance_arrieres import list_arrieres

        db = get_db()
        school_id = get_current_school_id()
        id_annee = request.args.get("id_annee")
        if id_annee:
            annee = tenant_query(AnneeScolaire).filter(AnneeScolaire.id == uuid.UUID(id_annee)).first()
        else:
            annee = tenant_query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()

        today = date.today()
        start_day = datetime.combine(today, datetime.min.time())

        # Encaissements du jour
        paiements_jour_q = (
            tenant_query(Paiement)
            .filter(Paiement.annule.is_(False), Paiement.date_paiement >= start_day)
        )
        if annee:
            paiements_jour_q = paiements_jour_q.filter(Paiement.id_annee == annee.id)
        paiements_jour = paiements_jour_q.all()
        encaissements_jour = {
            "count": len(paiements_jour),
            "montant": float(sum(float(p.montant_verse) for p in paiements_jour)),
            "items": [
                {
                    "id": str(p.id),
                    "montant": float(p.montant_verse),
                    "motif": p.motif,
                    "date": p.date_paiement.isoformat() if p.date_paiement else None,
                    "numero_recu": p.numero_recu,
                    "mode_paiement": p.mode_paiement,
                }
                for p in paiements_jour[:20]
            ],
        }

        paiements = (
            tenant_query(Paiement)
            .filter(Paiement.annule.is_(False))
            .order_by(Paiement.date_paiement.desc())
            .limit(30)
            .all()
        )
        recent = [
            {
                "id": str(p.id),
                "montant": float(p.montant_verse),
                "motif": p.motif,
                "date": p.date_paiement.isoformat() if p.date_paiement else None,
                "numero_recu": p.numero_recu,
                "mode_paiement": p.mode_paiement,
            }
            for p in paiements
        ]

        # Impayés (arriérés)
        impayes = {"nb": 0, "montant": 0.0, "top": []}
        recouvrement = None
        if annee:
            rows = list_arrieres(db, annee.id, school_id=school_id, as_of=today)
            arrears = [r for r in rows if r.get("arriere", 0) > 0]
            impayes = {
                "nb": len(arrears),
                "montant": float(sum(r["arriere"] for r in arrears)),
                "top": [
                    {
                        "id_eleve": str(r["id_eleve"]),
                        "matricule": r.get("matricule"),
                        "nom": r.get("nom"),
                        "prenom": r.get("prenom"),
                        "arriere": float(r["arriere"]),
                    }
                    for r in sorted(arrears, key=lambda x: -x["arriere"])[:10]
                ],
            }
            total_du = sum(r["total_du"] for r in rows)
            total_paye = sum(r["total_paye"] for r in rows)
            recouvrement = {
                "total_du": total_du,
                "total_paye": total_paye,
                "taux": round(total_paye / total_du * 100, 1) if total_du else 0,
                "nb_arrieres": len(arrears),
            }

        # Échéances dans les 7 jours
        until = today + timedelta(days=7)
        echeances_7j = []
        if annee:
            frais_ids = [
                f.id
                for f in tenant_query(FraisScolaire)
                .filter(FraisScolaire.id_annee == annee.id)
                .all()
            ]
            if frais_ids:
                ecs = (
                    db.query(EcheancePaiement)
                    .filter(
                        EcheancePaiement.id_frais.in_(frais_ids),
                        EcheancePaiement.date_echeance >= today,
                        EcheancePaiement.date_echeance <= until,
                    )
                    .order_by(EcheancePaiement.date_echeance)
                    .limit(30)
                    .all()
                )
                echeances_7j = [
                    {
                        "id": str(ec.id),
                        "libelle": ec.libelle,
                        "montant": float(ec.montant),
                        "date_echeance": ec.date_echeance.isoformat(),
                    }
                    for ec in ecs
                ]

        # Mobile Money « pending » : paiements MM du jour non encore rapprochés
        # (mode_paiement opérateur + pas de numéro de reçu définitif rare — heuristique)
        mm_modes = ("orange", "wave", "moov", "mtn", "mobile_money", "orange_money", "momo")
        mm_pending_items = [
            p for p in paiements_jour
            if (p.mode_paiement or "").strip().lower() in mm_modes
            or (p.numero_recu or "").upper().startswith("MM-")
            or (p.numero_recu or "").upper().startswith("SBX-")
        ]
        mm_pending = {
            "count": len(mm_pending_items),
            "montant": float(sum(float(p.montant_verse) for p in mm_pending_items)),
            "items": [
                {
                    "id": str(p.id),
                    "montant": float(p.montant_verse),
                    "numero_recu": p.numero_recu,
                    "mode_paiement": p.mode_paiement,
                }
                for p in mm_pending_items[:15]
            ],
        }

        return jsonify({
            "role": "comptable",
            "encaissements_jour": encaissements_jour,
            "impayes": impayes,
            "echeances_7j": echeances_7j,
            "mm_pending": mm_pending,
            "paiements_recents": recent,
            "recouvrement": recouvrement,
        })


@blp.route("/surveillant")
class DashboardSurveillant(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "surveillant")
    def get(self):
        """Vue surveillant : absences jour, retards, alertes décrochage, incidents."""
        from app.models import AlerteDecrochage, IncidentDisciplinaire, SortieEleve

        db = get_db()
        today = date.today()
        absences_jour = (
            tenant_query(Absence)
            .filter(Absence.date_absence == today)
            .count()
        )
        retards_jour = (
            tenant_query(Absence)
            .filter(
                Absence.date_absence == today,
                Absence.type_absence.in_(("retard", "Retard", "RETARD")),
            )
            .count()
        )

        alertes_decrochage = 0
        alertes_items = []
        try:
            alertes = (
                tenant_query(AlerteDecrochage)
                .filter(AlerteDecrochage.statut.in_(("ouverte", "en_cours")))
                .order_by(AlerteDecrochage.created_at.desc())
                .limit(15)
                .all()
            )
            alertes_decrochage = (
                tenant_query(AlerteDecrochage)
                .filter(AlerteDecrochage.statut.in_(("ouverte", "en_cours")))
                .count()
            )
            alertes_items = [
                {
                    "id": str(a.id),
                    "id_eleve": str(a.id_eleve),
                    "type_alerte": a.type_alerte,
                    "niveau": a.niveau,
                    "statut": a.statut,
                }
                for a in alertes
            ]
        except Exception:
            db.rollback()
            alertes_decrochage = 0
            alertes_items = []

        incidents_recent = []
        incidents_count = 0
        try:
            since = today - timedelta(days=14)
            incidents_q = (
                tenant_query(IncidentDisciplinaire)
                .filter(IncidentDisciplinaire.date_incident >= since)
                .order_by(IncidentDisciplinaire.date_incident.desc())
            )
            incidents_count = incidents_q.count()
            incidents_recent = [
                {
                    "id": str(i.id),
                    "id_eleve": str(i.id_eleve),
                    "type_incident": i.type_incident,
                    "date_incident": i.date_incident.isoformat() if i.date_incident else None,
                    "description": (i.description or "")[:120],
                }
                for i in incidents_q.limit(10).all()
            ]
        except Exception:
            db.rollback()

        sorties_ouvertes = 0
        try:
            sorties_ouvertes = (
                tenant_query(SortieEleve)
                .filter(SortieEleve.statut == "sorti", SortieEleve.heure_retour.is_(None))
                .count()
            )
        except Exception:
            db.rollback()
            sorties_ouvertes = 0

        abs_par_classe = get_absences_par_classe_dashboard(
            db,
            id_annee=uuid.UUID(request.args["id_annee"]) if request.args.get("id_annee") else None,
        )
        return jsonify({
            "role": "surveillant",
            "absences_aujourd_hui": absences_jour,
            "retards_aujourd_hui": retards_jour,
            "alertes_decrochage": alertes_decrochage,
            "alertes": alertes_items,
            "incidents_14j": incidents_count,
            "incidents": incidents_recent,
            "sorties_ouvertes": sorties_ouvertes,
            "absences_par_classe": abs_par_classe,
        })


@blp.route("/secretaire")
class DashboardSecretaire(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def get(self):
        """Vue secrétariat : inscriptions en cours, dossiers admission incomplets, encaissements."""
        from datetime import datetime

        from app.models import AdmissionDossier, AnneeScolaire

        school_id = get_current_school_id()
        id_annee = request.args.get("id_annee")
        if id_annee:
            annee = tenant_query(AnneeScolaire).filter(AnneeScolaire.id == uuid.UUID(id_annee)).first()
        else:
            annee = tenant_query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()

        # Inscriptions en cours (statut provisoire / en_attente / brouillon)
        insc_statuts = ("en_cours", "en_attente", "provisoire", "brouillon", "preinscrit")
        insc_q = tenant_query(Inscription).filter(Inscription.statut.in_(insc_statuts))
        if annee:
            insc_q = insc_q.filter(Inscription.id_annee == annee.id)
        inscriptions_en_cours = insc_q.count()
        insc_items = [
            {
                "id": str(i.id),
                "id_eleve": str(i.id_eleve),
                "statut": i.statut,
                "id_classe": str(i.id_classe) if i.id_classe else None,
            }
            for i in insc_q.order_by(Inscription.id.desc()).limit(15).all()
        ]

        # Dossiers admission incomplets
        incomplets_statuts = ("brouillon", "incomplet", "pieces_manquantes", "en_attente")
        dossiers_q = tenant_query(AdmissionDossier).filter(
            AdmissionDossier.statut.in_(incomplets_statuts)
        )
        if annee:
            dossiers_q = dossiers_q.filter(
                (AdmissionDossier.id_annee == annee.id) | (AdmissionDossier.id_annee.is_(None))
            )
        dossiers_incomplets = dossiers_q.count()
        dossier_items = [
            {
                "id": str(d.id),
                "nom": d.nom,
                "prenom": d.prenom,
                "statut": d.statut,
                "niveau_demande": d.niveau_demande,
            }
            for d in dossiers_q.order_by(AdmissionDossier.updated_at.desc()).limit(15).all()
        ]

        today = date.today()
        start_day = datetime.combine(today, datetime.min.time())
        paiements_jour = (
            tenant_query(Paiement)
            .filter(Paiement.annule.is_(False), Paiement.date_paiement >= start_day)
            .all()
        )
        encaissements = {
            "count": len(paiements_jour),
            "montant": float(sum(float(p.montant_verse) for p in paiements_jour)),
        }

        return jsonify({
            "role": "secretaire",
            "inscriptions_en_cours": inscriptions_en_cours,
            "inscriptions": insc_items,
            "dossiers_admission_incomplets": dossiers_incomplets,
            "dossiers": dossier_items,
            "encaissements_jour": encaissements,
            "school_id": str(school_id),
        })
