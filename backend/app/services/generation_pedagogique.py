"""Génération PDF pédagogiques (devoirs, compositions, fiches classe, enseignant)."""
import os
import uuid
from datetime import date, datetime, timezone

from flask import current_app, render_template

from app.extensions import get_db
from app.models import (
    AffectationEnseignant,
    AnneeScolaire,
    Classe,
    CreneauEmploiTemps,
    Eleve,
    Enseignant,
    Etablissement,
    Evaluation,
    Inscription,
    Matiere,
    ProgrammeDevoir,
    Trimestre,
)
from app.services.pdf_render import html_to_pdf

JOURS = {1: "Lundi", 2: "Mardi", 3: "Mercredi", 4: "Jeudi", 5: "Vendredi", 6: "Samedi", 7: "Dimanche"}


def _pdf_path(prefix: str) -> str:
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{prefix}_{uuid.uuid4().hex[:12]}.pdf")


def _etablissement(db):
    return db.query(Etablissement).first()


def _eleves_classe(db, id_classe: uuid.UUID):
    inscriptions = (
        db.query(Inscription)
        .filter(
            Inscription.id_classe == id_classe,
            Inscription.statut.in_(("inscrit", "reinscrit")),
        )
        .all()
    )
    eleves = []
    for ins in inscriptions:
        eleve = db.query(Eleve).filter(Eleve.id == ins.id_eleve).first()
        if eleve:
            eleves.append(eleve)
    return sorted(eleves, key=lambda e: (e.nom, e.prenom))


def generer_pdf_programme_devoirs(id_classe: uuid.UUID, id_annee: uuid.UUID) -> str:
    db = get_db()
    classe = db.query(Classe).filter(Classe.id == id_classe).first()
    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == id_annee).first()
    rows = (
        db.query(ProgrammeDevoir)
        .filter(ProgrammeDevoir.id_classe == id_classe, ProgrammeDevoir.id_annee == id_annee)
        .order_by(ProgrammeDevoir.jour_semaine, ProgrammeDevoir.id_matiere)
        .all()
    )
    items = []
    for row in rows:
        matiere = db.query(Matiere).filter(Matiere.id == row.id_matiere).first()
        items.append({
            "jour": JOURS.get(row.jour_semaine, str(row.jour_semaine)),
            "matiere": matiere.libelle if matiere else "—",
            "frequence": row.frequence,
            "note": row.note or "",
        })
    html = render_template(
        "programme_devoirs.html",
        etablissement=_etablissement(db),
        classe=classe,
        annee=annee,
        items=items,
        date_generation=datetime.now(timezone.utc),
    )
    path = _pdf_path("programme_devoirs")
    html_to_pdf(html, path)
    return path


def generer_pdf_calendrier_compositions(
    id_classe: uuid.UUID, id_trimestre: uuid.UUID, include_brouillon: bool = False
) -> str:
    db = get_db()
    classe = db.query(Classe).filter(Classe.id == id_classe).first()
    trimestre = db.query(Trimestre).filter(Trimestre.id == id_trimestre).first()
    annee = (
        db.query(AnneeScolaire).filter(AnneeScolaire.id == trimestre.id_annee).first()
        if trimestre
        else None
    )
    q = db.query(Evaluation).filter(
        Evaluation.id_classe == id_classe,
        Evaluation.id_trimestre == id_trimestre,
        Evaluation.type_evaluation == "examen",
    )
    if not include_brouillon:
        q = q.filter(Evaluation.statut_publication == "publie")
    evaluations = q.order_by(Evaluation.date_evaluation).all()
    items = []
    for ev in evaluations:
        matiere = db.query(Matiere).filter(Matiere.id == ev.id_matiere).first()
        items.append({
            "date": ev.date_evaluation.strftime("%d/%m/%Y"),
            "matiere": matiere.libelle if matiere else "—",
            "coefficient": float(ev.coefficient),
            "libelle": ev.libelle or "Composition",
            "statut": ev.statut_publication,
        })
    html = render_template(
        "calendrier_compositions.html",
        etablissement=_etablissement(db),
        classe=classe,
        trimestre=trimestre,
        annee=annee,
        items=items,
        date_generation=datetime.now(timezone.utc),
    )
    path = _pdf_path("calendrier_compositions")
    html_to_pdf(html, path)
    return path


def generer_pdf_fiche_enseignant(id_enseignant: uuid.UUID, id_annee: uuid.UUID) -> str:
    db = get_db()
    enseignant = db.query(Enseignant).filter(Enseignant.id == id_enseignant).first()
    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == id_annee).first()
    affectations = (
        db.query(AffectationEnseignant)
        .filter(
            AffectationEnseignant.id_enseignant == id_enseignant,
            AffectationEnseignant.id_annee == id_annee,
        )
        .all()
    )
    aff_rows = []
    volume_total = 0.0
    for aff in affectations:
        cls = db.query(Classe).filter(Classe.id == aff.id_classe).first()
        mat = db.query(Matiere).filter(Matiere.id == aff.id_matiere).first()
        vol = float(aff.volume_horaire_hebdo or 0)
        volume_total += vol
        aff_rows.append({
            "classe": cls.libelle if cls else "—",
            "matiere": mat.libelle if mat else "—",
            "volume": vol,
        })
    creneaux = []
    for aff in affectations:
        cls = db.query(Classe).filter(Classe.id == aff.id_classe).first()
        mat = db.query(Matiere).filter(Matiere.id == aff.id_matiere).first()
        for c in db.query(CreneauEmploiTemps).filter(CreneauEmploiTemps.id_affectation == aff.id).all():
            creneaux.append({
                "jour": JOURS.get(c.jour_semaine, str(c.jour_semaine)),
                "debut": c.heure_debut.strftime("%H:%M"),
                "fin": c.heure_fin.strftime("%H:%M"),
                "classe": cls.libelle if cls else "—",
                "matiere": mat.libelle if mat else "—",
            })
    creneaux.sort(key=lambda x: (list(JOURS.values()).index(x["jour"]) if x["jour"] in JOURS.values() else 99, x["debut"]))
    html = render_template(
        "fiche_enseignant.html",
        etablissement=_etablissement(db),
        enseignant=enseignant,
        annee=annee,
        affectations=aff_rows,
        volume_total=volume_total,
        creneaux=creneaux,
        date_generation=datetime.now(timezone.utc),
    )
    path = _pdf_path("fiche_enseignant")
    html_to_pdf(html, path)
    return path


def generer_pdf_liste_eleves(id_classe: uuid.UUID) -> str:
    db = get_db()
    classe = db.query(Classe).filter(Classe.id == id_classe).first()
    eleves = _eleves_classe(db, id_classe)
    html = render_template(
        "liste_eleves.html",
        etablissement=_etablissement(db),
        classe=classe,
        eleves=eleves,
        date_generation=datetime.now(timezone.utc),
    )
    path = _pdf_path("liste_eleves")
    html_to_pdf(html, path)
    return path


def generer_pdf_fiche_correction(id_evaluation: uuid.UUID) -> str:
    db = get_db()
    evaluation = db.query(Evaluation).filter(Evaluation.id == id_evaluation).first()
    if not evaluation:
        raise ValueError("Évaluation introuvable")
    classe = db.query(Classe).filter(Classe.id == evaluation.id_classe).first()
    matiere = db.query(Matiere).filter(Matiere.id == evaluation.id_matiere).first()
    trimestre = db.query(Trimestre).filter(Trimestre.id == evaluation.id_trimestre).first()
    eleves = _eleves_classe(db, evaluation.id_classe)
    html = render_template(
        "fiche_correction.html",
        etablissement=_etablissement(db),
        evaluation=evaluation,
        classe=classe,
        matiere=matiere,
        trimestre=trimestre,
        eleves=eleves,
        date_generation=datetime.now(timezone.utc),
    )
    path = _pdf_path("fiche_correction")
    html_to_pdf(html, path)
    return path


def generer_pdf_fiche_appel(id_classe: uuid.UUID, date_appel: date | None = None) -> str:
    db = get_db()
    classe = db.query(Classe).filter(Classe.id == id_classe).first()
    eleves = _eleves_classe(db, id_classe)
    date_appel = date_appel or date.today()
    html = render_template(
        "fiche_appel.html",
        etablissement=_etablissement(db),
        classe=classe,
        eleves=eleves,
        date_appel=date_appel,
        date_generation=datetime.now(timezone.utc),
    )
    path = _pdf_path("fiche_appel")
    html_to_pdf(html, path)
    return path


def generer_pdf_fiche_scolarite(id_classe: uuid.UUID, id_annee: uuid.UUID) -> str:
    db = get_db()
    from sqlalchemy import text

    classe = db.query(Classe).filter(Classe.id == id_classe).first()
    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == id_annee).first()
    rows = db.execute(
        text("""
            SELECT
                e.matricule, e.nom, e.prenom,
                COALESCE(SUM(ec.montant), 0) AS total_du,
                COALESCE((
                    SELECT SUM(p.montant_verse)
                    FROM paiement p
                    WHERE p.id_eleve = i.id_eleve AND p.id_annee = :id_annee AND p.annule = false
                ), 0) AS total_paye
            FROM inscription i
            JOIN eleve e ON e.id = i.id_eleve
            JOIN classe c ON c.id = i.id_classe
            JOIN frais_scolaire fs ON fs.id_niveau = c.id_niveau AND fs.id_annee = i.id_annee
            JOIN echeance_paiement ec ON ec.id_frais = fs.id
            WHERE i.id_annee = :id_annee AND i.id_classe = :id_classe
              AND i.statut IN ('inscrit', 'reinscrit')
            GROUP BY e.matricule, e.nom, e.prenom, i.id_eleve
            ORDER BY e.nom, e.prenom
        """),
        {"id_annee": id_annee, "id_classe": id_classe},
    ).fetchall()
    eleves = [
        {
            "matricule": r[0],
            "nom": r[1],
            "prenom": r[2],
            "total_du": float(r[3]),
            "montant_paye": float(r[4]),
            "arriere": round(float(r[3]) - float(r[4]), 2),
        }
        for r in rows
    ]
    html = render_template(
        "fiche_scolarite.html",
        etablissement=_etablissement(db),
        classe=classe,
        annee=annee,
        eleves=eleves,
        date_generation=datetime.now(timezone.utc),
    )
    path = _pdf_path("fiche_scolarite")
    html_to_pdf(html, path)
    return path


def generer_pdf_emargement_composition(id_evaluation: uuid.UUID) -> str:
    db = get_db()
    evaluation = db.query(Evaluation).filter(Evaluation.id == id_evaluation).first()
    if not evaluation:
        raise ValueError("Évaluation introuvable")
    classe = db.query(Classe).filter(Classe.id == evaluation.id_classe).first()
    matiere = db.query(Matiere).filter(Matiere.id == evaluation.id_matiere).first()
    eleves = _eleves_classe(db, evaluation.id_classe)
    html = render_template(
        "emargement_composition.html",
        etablissement=_etablissement(db),
        evaluation=evaluation,
        classe=classe,
        matiere=matiere,
        eleves=eleves,
        date_generation=datetime.now(timezone.utc),
    )
    path = _pdf_path("emargement_composition")
    html_to_pdf(html, path)
    return path


def generer_pdf_programme_trimestriel(
    id_classe: uuid.UUID, id_trimestre: uuid.UUID, id_annee: uuid.UUID
) -> str:
    """Export combiné devoirs + compositions + emploi du temps pour une classe."""
    db = get_db()
    classe = db.query(Classe).filter(Classe.id == id_classe).first()
    trimestre = db.query(Trimestre).filter(Trimestre.id == id_trimestre).first()
    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == id_annee).first()

    devoirs_rows = (
        db.query(ProgrammeDevoir)
        .filter(ProgrammeDevoir.id_classe == id_classe, ProgrammeDevoir.id_annee == id_annee)
        .order_by(ProgrammeDevoir.jour_semaine)
        .all()
    )
    devoirs = []
    for row in devoirs_rows:
        matiere = db.query(Matiere).filter(Matiere.id == row.id_matiere).first()
        devoirs.append({
            "jour": JOURS.get(row.jour_semaine, str(row.jour_semaine)),
            "matiere": matiere.libelle if matiere else "—",
            "frequence": row.frequence,
        })

    compositions = (
        db.query(Evaluation)
        .filter(
            Evaluation.id_classe == id_classe,
            Evaluation.id_trimestre == id_trimestre,
            Evaluation.type_evaluation == "examen",
            Evaluation.statut_publication == "publie",
        )
        .order_by(Evaluation.date_evaluation)
        .all()
    )
    comp_items = []
    for ev in compositions:
        matiere = db.query(Matiere).filter(Matiere.id == ev.id_matiere).first()
        comp_items.append({
            "date": ev.date_evaluation.strftime("%d/%m/%Y"),
            "matiere": matiere.libelle if matiere else "—",
            "libelle": ev.libelle or "Composition",
            "coefficient": float(ev.coefficient),
        })

    affectations = (
        db.query(AffectationEnseignant)
        .filter(AffectationEnseignant.id_classe == id_classe, AffectationEnseignant.id_annee == id_annee)
        .all()
    )
    creneaux = []
    for aff in affectations:
        mat = db.query(Matiere).filter(Matiere.id == aff.id_matiere).first()
        ens = db.query(Enseignant).filter(Enseignant.id == aff.id_enseignant).first()
        for c in db.query(CreneauEmploiTemps).filter(CreneauEmploiTemps.id_affectation == aff.id).all():
            creneaux.append({
                "jour": JOURS.get(c.jour_semaine, str(c.jour_semaine)),
                "debut": c.heure_debut.strftime("%H:%M"),
                "fin": c.heure_fin.strftime("%H:%M"),
                "matiere": mat.libelle if mat else "—",
                "enseignant": f"{ens.prenom} {ens.nom}" if ens else "—",
            })
    creneaux.sort(key=lambda x: (list(JOURS.values()).index(x["jour"]) if x["jour"] in JOURS.values() else 99, x["debut"]))

    html = render_template(
        "programme_trimestriel.html",
        etablissement=_etablissement(db),
        classe=classe,
        trimestre=trimestre,
        annee=annee,
        devoirs=devoirs,
        compositions=comp_items,
        creneaux=creneaux,
        date_generation=datetime.now(timezone.utc),
    )
    path = _pdf_path("programme_trimestriel")
    html_to_pdf(html, path)
    return path
