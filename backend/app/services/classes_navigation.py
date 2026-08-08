"""Services de navigation Cycle → Classe."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models import Absence, Classe, Inscription, NiveauEtude


def _active_annee_id(db: Session, id_annee: uuid.UUID | None) -> uuid.UUID | None:
    if id_annee:
        return id_annee
    from app.models import AnneeScolaire

    active = db.query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
    return active.id if active else None


def get_classes_navigation(
    db: Session,
    *,
    cycle: str | None = None,
    id_annee: uuid.UUID | None = None,
    class_ids: list[uuid.UUID] | None = None,
) -> list[dict]:
    """Liste des classes enrichies (effectif, absences jour, non justifiées en attente)."""
    annee_id = _active_annee_id(db, id_annee)
    if not annee_id:
        return []

    today = date.today()
    pending_since = today - timedelta(days=7)

    q = (
        db.query(Classe, NiveauEtude)
        .join(NiveauEtude, NiveauEtude.id == Classe.id_niveau)
        .filter(Classe.id_annee == annee_id)
    )
    if cycle:
        q = q.filter(NiveauEtude.cycle == cycle)
    if class_ids is not None:
        if not class_ids:
            return []
        q = q.filter(Classe.id.in_(class_ids))

    rows = q.order_by(NiveauEtude.ordre, Classe.libelle).all()
    results = []
    for classe, niveau in rows:
        effectif = (
            db.query(func.count(Inscription.id))
            .filter(
                Inscription.id_classe == classe.id,
                Inscription.id_annee == annee_id,
                Inscription.statut.in_(("inscrit", "reinscrit")),
            )
            .scalar()
            or 0
        )

        eleve_ids = [
            r[0]
            for r in db.query(Inscription.id_eleve)
            .filter(
                Inscription.id_classe == classe.id,
                Inscription.id_annee == annee_id,
                Inscription.statut.in_(("inscrit", "reinscrit")),
            )
            .all()
        ]

        absences_jour = 0
        non_justifiees = 0
        if eleve_ids:
            absences_jour = (
                db.query(func.count(Absence.id))
                .filter(Absence.id_eleve.in_(eleve_ids), Absence.date_absence == today)
                .scalar()
                or 0
            )
            non_justifiees = (
                db.query(func.count(Absence.id))
                .filter(
                    Absence.id_eleve.in_(eleve_ids),
                    Absence.justifiee.is_(False),
                    Absence.date_absence >= pending_since,
                )
                .scalar()
                or 0
            )

        results.append(
            {
                "id": str(classe.id),
                "libelle": classe.libelle,
                "id_niveau": str(classe.id_niveau),
                "niveau_libelle": niveau.libelle,
                "cycle": niveau.cycle,
                "effectif": effectif,
                "absences_jour": absences_jour,
                "non_justifiees_en_attente": non_justifiees,
            }
        )
    return results


def get_absences_par_classe_dashboard(
    db: Session,
    *,
    id_annee: uuid.UUID | None = None,
    jours_non_justifiees: int = 7,
) -> dict:
    """Absences du jour et non justifiées en attente, groupées par cycle puis classe."""
    annee_id = _active_annee_id(db, id_annee)
    if not annee_id:
        return {"absences_jour": [], "non_justifiees_en_attente": []}

    today = date.today()
    pending_since = today - timedelta(days=jours_non_justifiees)

    def _group(rows):
        cycles: dict[str, dict] = {}
        for cycle, classe_id, libelle, count in rows:
            if cycle not in cycles:
                cycles[cycle] = {"cycle": cycle, "total": 0, "classes": []}
            cycles[cycle]["total"] += count
            cycles[cycle]["classes"].append(
                {"id_classe": str(classe_id), "libelle": libelle, "count": count}
            )
        order = {"premier": 0, "second": 1}
        return sorted(cycles.values(), key=lambda c: order.get(c["cycle"], 99))

    jour_rows = db.execute(
        text("""
            SELECT ne.cycle, c.id, c.libelle, COUNT(a.id) AS cnt
            FROM absence a
            JOIN eleve e ON e.id = a.id_eleve
            JOIN inscription i ON i.id_eleve = e.id AND i.id_annee = :id_annee
                AND i.statut IN ('inscrit', 'reinscrit')
            JOIN classe c ON c.id = i.id_classe
            JOIN niveau_etude ne ON ne.id = c.id_niveau
            WHERE a.date_absence = :today
            GROUP BY ne.cycle, c.id, c.libelle, ne.ordre
            ORDER BY ne.ordre, c.libelle
        """),
        {"id_annee": annee_id, "today": today},
    ).fetchall()

    pending_rows = db.execute(
        text("""
            SELECT ne.cycle, c.id, c.libelle, COUNT(a.id) AS cnt
            FROM absence a
            JOIN eleve e ON e.id = a.id_eleve
            JOIN inscription i ON i.id_eleve = e.id AND i.id_annee = :id_annee
                AND i.statut IN ('inscrit', 'reinscrit')
            JOIN classe c ON c.id = i.id_classe
            JOIN niveau_etude ne ON ne.id = c.id_niveau
            WHERE a.justifiee = false AND a.date_absence >= :pending_since
            GROUP BY ne.cycle, c.id, c.libelle, ne.ordre
            ORDER BY ne.ordre, c.libelle
        """),
        {"id_annee": annee_id, "pending_since": pending_since},
    ).fetchall()

    return {
        "absences_jour": _group(jour_rows),
        "non_justifiees_en_attente": _group(pending_rows),
    }
