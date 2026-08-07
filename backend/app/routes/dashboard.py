"""Module 8 — Tableau de bord BI."""
from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from sqlalchemy import func, text

from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import Absence, Inscription, Paiement

blp = Blueprint("dashboard", __name__, url_prefix="/dashboard", description="Tableau de bord")


@blp.route("/stats")
class DashboardStats(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "agent_comptable", "secretariat")
    def get(self):
        db = get_db()
        id_annee = request.args.get("id_annee")

        effectifs_query = db.execute(
            text("""
                SELECT ne.libelle AS niveau, e.sexe, COUNT(DISTINCT i.id_eleve) AS effectif
                FROM inscription i
                JOIN eleve e ON e.id = i.id_eleve
                JOIN classe c ON c.id = i.id_classe
                JOIN niveau_etude ne ON ne.id = c.id_niveau
                WHERE i.statut IN ('inscrit', 'reinscrit')
                  AND (:id_annee IS NULL OR i.id_annee = CAST(:id_annee AS UUID))
                GROUP BY ne.libelle, ne.ordre, e.sexe
                ORDER BY ne.ordre, e.sexe
            """),
            {"id_annee": id_annee},
        ).fetchall()

        effectifs = [
            {"niveau": r[0], "sexe": r[1], "effectif": r[2]} for r in effectifs_query
        ]

        taux_reussite = []
        try:
            reussite_query = db.execute(
                text("""
                    SELECT mat.libelle,
                           COUNT(*) AS total,
                           COUNT(*) FILTER (WHERE m.moyenne >= 10) AS reussis
                    FROM moyenne_matiere_eleve m
                    JOIN matiere mat ON mat.id = m.id_matiere
                    GROUP BY mat.libelle
                """)
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
            taux_reussite = []

        tresorerie = 0
        total_du = 0
        if id_annee:
            paiements = (
                db.query(func.coalesce(func.sum(Paiement.montant_verse), 0))
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
                      AND i.statut IN ('inscrit', 'reinscrit')
                """),
                {"id_annee": id_annee},
            ).scalar()
            total_du = float(du or 0)

        taux_recouvrement = round(tresorerie / total_du * 100, 1) if total_du > 0 else 0

        inscrits_q = db.query(func.count(Inscription.id)).filter(
            Inscription.statut.in_(("inscrit", "reinscrit"))
        )
        if id_annee:
            inscrits_q = inscrits_q.filter(Inscription.id_annee == id_annee)
        total_eleves = inscrits_q.scalar()

        absences_mois = db.query(func.count(Absence.id)).scalar() or 0

        return jsonify({
            "effectifs_par_niveau": effectifs,
            "taux_reussite_par_matiere": taux_reussite,
            "tresorerie": tresorerie,
            "total_du": total_du,
            "taux_recouvrement": taux_recouvrement,
            "total_eleves_inscrits": total_eleves,
            "total_absences": absences_mois,
        })
