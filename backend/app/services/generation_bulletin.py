"""Génération de bulletins PDF via WeasyPrint."""
import os
import uuid
from datetime import datetime, timezone

from flask import current_app, render_template
from sqlalchemy import text

from app.extensions import get_db
from app.services.pdf_render import html_to_pdf
from app.models import (
    Bulletin,
    Classe,
    CoefficientMatiere,
    Eleve,
    Etablissement,
    IncidentDisciplinaire,
    Inscription,
    Matiere,
    NiveauEtude,
    Trimestre,
)
from app.services.calcul_moyennes import (
    calculer_moyenne_generale,
    calculer_rangs,
    determiner_mention,
    refresh_moyenne_matiere_view,
)
from app.utils.audit_logger import log_audit


def _get_moyennes_eleve(db, id_eleve, id_classe, id_trimestre):
    """Récupère les moyennes par matière depuis la vue matérialisée."""
    rows = db.execute(
        text("""
            SELECT m.id_matiere, mat.libelle, m.moyenne, cm.coefficient
            FROM moyenne_matiere_eleve m
            JOIN matiere mat ON mat.id = m.id_matiere
            LEFT JOIN classe c ON c.id = m.id_classe
            LEFT JOIN coefficient_matiere cm ON cm.id_matiere = m.id_matiere
                AND cm.id_niveau = c.id_niveau
            WHERE m.id_eleve = :id_eleve AND m.id_trimestre = :id_trimestre
        """),
        {"id_eleve": id_eleve, "id_trimestre": id_trimestre},
    ).fetchall()
    return [
        {
            "id_matiere": r[0],
            "libelle": r[1],
            "moyenne": float(r[2]) if r[2] is not None else None,
            "coefficient": float(r[3]) if r[3] is not None else 1,
        }
        for r in rows
    ]


def _appreciation_discipline(db, id_eleve, id_trimestre) -> str | None:
    """Synthèse des incidents disciplinaires du trimestre pour le bulletin."""
    incidents = (
        db.query(IncidentDisciplinaire)
        .filter(
            IncidentDisciplinaire.id_eleve == id_eleve,
            IncidentDisciplinaire.id_trimestre == id_trimestre,
        )
        .order_by(IncidentDisciplinaire.date_incident)
        .all()
    )
    if not incidents:
        return None
    lines = []
    for inc in incidents:
        desc = inc.description or inc.type_incident or "Incident"
        lines.append(f"• {inc.date_incident} : {desc}")
    return "Discipline — incidents du trimestre :\n" + "\n".join(lines)


def generer_bulletin(id_eleve: uuid.UUID, id_trimestre: uuid.UUID, id_utilisateur: uuid.UUID) -> Bulletin:
    """Génère ou met à jour un bulletin en brouillon avec calcul des moyennes."""
    db = get_db()
    refresh_moyenne_matiere_view(db)

    eleve = db.query(Eleve).filter(Eleve.id == id_eleve).first()
    trimestre = db.query(Trimestre).filter(Trimestre.id == id_trimestre).first()
    if not eleve or not trimestre:
        raise ValueError("Élève ou trimestre introuvable")

    inscription = (
        db.query(Inscription)
        .filter(Inscription.id_eleve == id_eleve, Inscription.id_annee == trimestre.id_annee)
        .first()
    )
    if not inscription:
        raise ValueError("Inscription introuvable pour cet élève")

    id_classe = inscription.id_classe
    moyennes_mat = _get_moyennes_eleve(db, id_eleve, id_classe, id_trimestre)
    moy_gen = calculer_moyenne_generale(
        [{"moyenne": m["moyenne"], "coefficient_matiere": m["coefficient"]} for m in moyennes_mat]
    )

    # Moyennes de toute la classe pour rang et moyenne classe
    inscriptions_classe = db.query(Inscription).filter(Inscription.id_classe == id_classe).all()
    moyennes_classe = {}
    for ins in inscriptions_classe:
        mats = _get_moyennes_eleve(db, ins.id_eleve, id_classe, id_trimestre)
        mg = calculer_moyenne_generale(
            [{"moyenne": m["moyenne"], "coefficient_matiere": m["coefficient"]} for m in mats]
        )
        moyennes_classe[ins.id_eleve] = mg

    rangs = calculer_rangs(moyennes_classe)
    moyennes_valides = [m for m in moyennes_classe.values() if m is not None]
    moy_classe = sum(moyennes_valides) / len(moyennes_valides) if moyennes_valides else None

    bulletin = db.query(Bulletin).filter(
        Bulletin.id_eleve == id_eleve, Bulletin.id_trimestre == id_trimestre
    ).first()

    if bulletin and bulletin.statut == "publie":
        raise ValueError("Bulletin publié — lecture seule")

    if not bulletin:
        bulletin = Bulletin(
            id=uuid.uuid4(),
            id_eleve=id_eleve,
            id_trimestre=id_trimestre,
        )
        db.add(bulletin)

    bulletin.moyenne_generale = moy_gen
    bulletin.rang = rangs.get(id_eleve)
    bulletin.effectif_classe = len(inscriptions_classe)
    bulletin.moyenne_classe = round(moy_classe, 2) if moy_classe else None
    bulletin.mention = determiner_mention(moy_gen)
    bulletin.statut = bulletin.statut or "brouillon"
    discipline_text = _appreciation_discipline(db, id_eleve, id_trimestre)
    if discipline_text:
        existing = (bulletin.appreciation_generale or "").strip()
        bulletin.appreciation_generale = (
            f"{existing}\n\n{discipline_text}".strip() if existing else discipline_text
        )
    db.commit()

    return bulletin


def generer_bulletin_pdf(bulletin: Bulletin) -> str:
    """Génère le PDF du bulletin et retourne le chemin du fichier."""
    db = get_db()
    eleve = db.query(Eleve).filter(Eleve.id == bulletin.id_eleve).first()
    trimestre = db.query(Trimestre).filter(Trimestre.id == bulletin.id_trimestre).first()
    etablissement = db.query(Etablissement).first()
    from app.models import AnneeScolaire

    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == trimestre.id_annee).first() if trimestre else None

    inscription = (
        db.query(Inscription)
        .filter(Inscription.id_eleve == bulletin.id_eleve, Inscription.id_annee == trimestre.id_annee)
        .first()
    )
    classe = db.query(Classe).filter(Classe.id == inscription.id_classe).first() if inscription else None
    moyennes = _get_moyennes_eleve(db, bulletin.id_eleve, classe.id if classe else None, bulletin.id_trimestre)

    html = render_template(
        "bulletin.html",
        etablissement=etablissement,
        eleve=eleve,
        trimestre=trimestre,
        annee=annee,
        classe=classe,
        bulletin=bulletin,
        moyennes=moyennes,
        date_generation=datetime.now(timezone.utc),
    )

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "bulletins")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"bulletin_{bulletin.id_eleve}_{bulletin.id_trimestre}.pdf"
    filepath = os.path.join(upload_dir, filename)
    html_to_pdf(html, filepath)

    bulletin.pdf_url = filepath
    db.commit()
    return filepath


def valider_bulletin(bulletin_id: uuid.UUID, id_utilisateur: uuid.UUID) -> Bulletin:
    """Valide un bulletin (directeur/admin)."""
    db = get_db()
    bulletin = db.query(Bulletin).filter(Bulletin.id == bulletin_id).first()
    if not bulletin:
        raise ValueError("Bulletin introuvable")
    if bulletin.statut == "publie":
        raise ValueError("Bulletin déjà publié")
    bulletin.statut = "valide"
    bulletin.valide_par = id_utilisateur
    db.commit()
    log_audit("VALIDATION_BULLETIN", id_utilisateur, "bulletin", bulletin.id)
    return bulletin


def publier_bulletin(bulletin_id: uuid.UUID, id_utilisateur: uuid.UUID) -> Bulletin:
    """Publie un bulletin validé."""
    db = get_db()
    bulletin = db.query(Bulletin).filter(Bulletin.id == bulletin_id).first()
    if not bulletin:
        raise ValueError("Bulletin introuvable")
    if bulletin.statut != "valide":
        raise ValueError("Le bulletin doit être validé avant publication")
    generer_bulletin_pdf(bulletin)
    bulletin.statut = "publie"
    db.commit()
    log_audit("PUBLICATION_BULLETIN", id_utilisateur, "bulletin", bulletin.id)

    from app.services.envoi_notification import creer_notification

    eleve = db.query(Eleve).filter(Eleve.id == bulletin.id_eleve).first()
    trimestre = db.query(Trimestre).filter(Trimestre.id == bulletin.id_trimestre).first()
    if eleve and trimestre:
        creer_notification(
            "email",
            "publication_bulletin",
            f"Le bulletin du trimestre {trimestre.numero} de {eleve.prenom} {eleve.nom} est disponible.",
            id_eleve=bulletin.id_eleve,
        )

    return bulletin
