"""Statistiques de charge de travail pédagogique par classe."""
import uuid
from collections import defaultdict
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import AnneeScolaire, Classe, Evaluation, Matiere, ProgrammeDevoir, Trimestre
from app.services.tenant import get_current_school_id, get_or_404_tenant, tenant_query

JOURS = {1: "Lundi", 2: "Mardi", 3: "Mercredi", 4: "Jeudi", 5: "Vendredi", 6: "Samedi", 7: "Dimanche"}


def stats_charge_classe(
    db: Session,
    id_classe: uuid.UUID,
    id_annee: uuid.UUID,
    id_trimestre: uuid.UUID | None = None,
) -> dict:
    """Agrège devoirs récurrents (par jour) et compositions (par semaine)."""
    get_or_404_tenant(Classe, id_classe)
    get_or_404_tenant(AnneeScolaire, id_annee)
    devoirs = (
        db.query(ProgrammeDevoir)
        .join(Classe, ProgrammeDevoir.id_classe == Classe.id)
        .filter(
            ProgrammeDevoir.id_classe == id_classe,
            ProgrammeDevoir.id_annee == id_annee,
            Classe.school_id == get_current_school_id(),
        )
        .all()
    )
    par_jour = defaultdict(list)
    for d in devoirs:
        mat = tenant_query(Matiere).filter(Matiere.id == d.id_matiere).first()
        par_jour[d.jour_semaine].append({
            "matiere": mat.libelle if mat else "—",
            "frequence": d.frequence,
        })

    devoirs_stats = []
    alertes = []
    for jour, items in sorted(par_jour.items()):
        entry = {"jour": JOURS.get(jour, str(jour)), "jour_semaine": jour, "nb_devoirs": len(items), "matieres": items}
        devoirs_stats.append(entry)
        if len(items) >= 3:
            alertes.append(f"{entry['jour']} : {len(items)} matières avec devoir prévu")

    comp_q = tenant_query(Evaluation).filter(
        Evaluation.id_classe == id_classe,
        Evaluation.type_evaluation == "examen",
    )
    if id_trimestre:
        comp_q = comp_q.filter(Evaluation.id_trimestre == id_trimestre)
    compositions = comp_q.all()

    par_semaine = defaultdict(list)
    for ev in compositions:
        iso = ev.date_evaluation.isocalendar()
        key = f"{iso.year}-S{iso.week:02d}"
        mat = tenant_query(Matiere).filter(Matiere.id == ev.id_matiere).first()
        par_semaine[key].append({
            "date": ev.date_evaluation.isoformat(),
            "matiere": mat.libelle if mat else "—",
            "libelle": ev.libelle or "Composition",
        })

    semaines_stats = []
    for semaine, items in sorted(par_semaine.items()):
        entry = {"semaine": semaine, "nb_compositions": len(items), "compositions": items}
        semaines_stats.append(entry)
        if len(items) >= 3:
            alertes.append(f"Semaine {semaine} : {len(items)} compositions programmées")

    trimestre = None
    if id_trimestre:
        trimestre = (
            db.query(Trimestre)
            .join(AnneeScolaire, Trimestre.id_annee == AnneeScolaire.id)
            .filter(
                Trimestre.id == id_trimestre,
                AnneeScolaire.school_id == get_current_school_id(),
            )
            .first()
        )
    if trimestre:
        for d in range((trimestre.date_fin - trimestre.date_debut).days + 1):
            jour_date = trimestre.date_debut + timedelta(days=d)
            iso = jour_date.isocalendar()
            key = f"{iso.year}-S{iso.week:02d}"
            jour_sem = jour_date.isoweekday()
            nb_devoirs_jour = len(par_jour.get(jour_sem, []))
            comps_semaine = len(par_semaine.get(key, []))
            if nb_devoirs_jour >= 3 and comps_semaine >= 2:
                alertes.append(
                    f"Semaine du {jour_date.strftime('%d/%m/%Y')} : charge élevée "
                    f"({nb_devoirs_jour} devoirs le {JOURS.get(jour_sem)} + {comps_semaine} compositions)"
                )

    return {
        "devoirs_par_jour": devoirs_stats,
        "compositions_par_semaine": semaines_stats,
        "alertes": alertes,
        "surcharge": len(alertes) > 0,
    }
