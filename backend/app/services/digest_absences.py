"""Digest hebdomadaire des absences — établissement + parents (idempotent)."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Absence, Classe, Eleve, EleveParent, Inscription, Notification, ParentTuteur
from app.services.envoi_notification import (
    creer_notification,
    traiter_file_notifications,
)


def iso_week_bounds(ref: date | None = None) -> tuple[date, date, str]:
    """Retourne (lundi, dimanche, clé ISO YYYY-Www) pour la semaine de ref (défaut: semaine précédente)."""
    today = ref or date.today()
    # Par défaut : semaine civile précédente (digest généré en début de semaine suivante).
    target = today - timedelta(days=7) if ref is None else today
    monday = target - timedelta(days=target.weekday())
    sunday = monday + timedelta(days=6)
    iso_year, iso_week, _ = monday.isocalendar()
    week_key = f"{iso_year}-W{iso_week:02d}"
    return monday, sunday, week_key


def _classe_id_for_eleve(db: Session, school_id: uuid.UUID, id_eleve: uuid.UUID) -> uuid.UUID | None:
    insc = (
        db.query(Inscription)
        .filter(
            Inscription.school_id == school_id,
            Inscription.id_eleve == id_eleve,
            Inscription.statut.in_(("inscrit", "reinscrit")),
        )
        .order_by(Inscription.date_inscription.desc())
        .first()
    )
    return insc.id_classe if insc else None


def _absences_semaine(
    db: Session,
    school_id: uuid.UUID,
    debut: date,
    fin: date,
) -> list[Absence]:
    return (
        db.query(Absence)
        .filter(
            Absence.school_id == school_id,
            Absence.date_absence >= debut,
            Absence.date_absence <= fin,
        )
        .order_by(Absence.date_absence.asc())
        .all()
    )


def _existing_by_key(db: Session, school_id: uuid.UUID, key: str) -> Notification | None:
    return (
        db.query(Notification)
        .filter(
            Notification.school_id == school_id,
            Notification.idempotency_key == key,
        )
        .first()
    )


def _format_absence_line(db: Session, absences: list[Absence]) -> str:
    lines = []
    for a in absences:
        eleve = db.query(Eleve).filter(Eleve.id == a.id_eleve).first()
        nom = f"{eleve.prenom} {eleve.nom}" if eleve else str(a.id_eleve)
        justif = "justifiée" if a.justifiee else "non justifiée"
        motif = a.motif or "—"
        lines.append(f"- {a.date_absence.isoformat()} — {nom} ({justif}) — {motif}")
    return "\n".join(lines)


def digest_absences_hebdo(
    db: Session,
    school_id: uuid.UUID,
    *,
    ref_date: date | None = None,
    canal: str = "email",
    auto_envoyer: bool = False,
) -> dict:
    """
    Génère le digest hebdomadaire des absences.

    A. Une notification établissement (type digest_absences_etablissement).
    B. Une notification par parent regroupant tous ses enfants (digest_absences).

    Idempotence : clé déterministe school+type+semaine(+parent).
    """
    debut, fin, week_key = iso_week_bounds(ref_date)
    absences = _absences_semaine(db, school_id, debut, fin)

    eleves_ids = {a.id_eleve for a in absences}
    par_classe: dict[uuid.UUID, int] = defaultdict(int)
    for a in absences:
        cid = _classe_id_for_eleve(db, school_id, a.id_eleve)
        if cid:
            par_classe[cid] += 1

    classe_lines = []
    for cid, count in sorted(par_classe.items(), key=lambda x: -x[1]):
        classe = db.query(Classe).filter(Classe.id == cid).first()
        libelle = classe.libelle if classe else str(cid)
        classe_lines.append(f"- {libelle} : {count}")

    admin_key = f"digest_absences_etablissement:{school_id}:{week_key}"
    admin_created = False
    if not _existing_by_key(db, school_id, admin_key):
        contenu_admin = (
            f"Récapitulatif des absences — semaine {week_key}\n"
            f"Période : {debut.isoformat()} → {fin.isoformat()}\n"
            f"Total absences : {len(absences)}\n"
            f"Élèves concernés : {len(eleves_ids)}\n"
            f"Répartition par classe :\n"
            + ("\n".join(classe_lines) if classe_lines else "- Aucune")
            + "\n\nDétails :\n"
            + (_format_absence_line(db, absences) if absences else "- Aucune absence")
        )
        creer_notification(
            canal="interne",
            type_notification="digest_absences_etablissement",
            contenu=contenu_admin,
            school_id=school_id,
            idempotency_key=admin_key,
        )
        admin_created = True

    # Grouper absences par parent (tous les parents liés, pas seulement tuteur légal)
    by_parent: dict[uuid.UUID, list[Absence]] = defaultdict(list)
    for a in absences:
        links = db.query(EleveParent).filter(EleveParent.id_eleve == a.id_eleve).all()
        for link in links:
            by_parent[link.id_parent].append(a)

    parents_created = 0
    parents_ignored = 0
    for id_parent, parent_absences in by_parent.items():
        parent = (
            db.query(ParentTuteur)
            .filter(ParentTuteur.id == id_parent, ParentTuteur.school_id == school_id)
            .first()
        )
        if not parent:
            continue

        parent_key = f"digest_absences_parent:{school_id}:{id_parent}:{week_key}"
        if _existing_by_key(db, school_id, parent_key):
            parents_ignored += 1
            continue

        # Regrouper par enfant
        by_child: dict[uuid.UUID, list[Absence]] = defaultdict(list)
        for a in parent_absences:
            by_child[a.id_eleve].append(a)

        blocks = []
        for eid, child_abs in sorted(by_child.items(), key=lambda x: x[0].hex):
            eleve = db.query(Eleve).filter(Eleve.id == eid).first()
            nom = f"{eleve.prenom} {eleve.nom}" if eleve else str(eid)
            detail = "\n".join(
                f"  • {a.date_absence.isoformat()} — "
                f"{'justifiée' if a.justifiee else 'non justifiée'}"
                + (f" ({a.motif})" if a.motif else "")
                for a in child_abs
            )
            blocks.append(f"{nom} : {len(child_abs)} absence(s)\n{detail}")

        contenu = (
            f"Récapitulatif des absences de vos enfants — semaine {week_key}\n"
            f"Période : {debut.isoformat()} → {fin.isoformat()}\n\n"
            + "\n\n".join(blocks)
        )

        # Inbox interne + canal externe (email/sms) si demandé
        creer_notification(
            canal="interne",
            type_notification="digest_absences",
            contenu=contenu,
            id_parent=id_parent,
            school_id=school_id,
            idempotency_key=parent_key,
        )
        if canal in ("email", "sms"):
            # Clé distincte pour le canal externe (évite collision unique avec interne)
            creer_notification(
                canal=canal,
                type_notification="digest_absences",
                contenu=contenu,
                id_parent=id_parent,
                school_id=school_id,
                idempotency_key=f"{parent_key}:{canal}",
            )
        parents_created += 1

    envoyees = 0
    if auto_envoyer:
        envoyees = traiter_file_notifications(school_id=school_id)

    return {
        "week_key": week_key,
        "periode": {"debut": debut.isoformat(), "fin": fin.isoformat()},
        "total_absences": len(absences),
        "eleves_concernes": len(eleves_ids),
        "admin_digest_cree": admin_created,
        "parents_digest_crees": parents_created,
        "parents_ignores": parents_ignored,
        "envoyees": envoyees,
        "generated_at": datetime.now(UTC).isoformat(),
    }
