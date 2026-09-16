"""Génération de bulletins PDF via WeasyPrint."""
import os
import uuid
from datetime import UTC, datetime

from flask import abort, current_app, render_template

from app.extensions import get_db
from app.models import (
    AnneeScolaire,
    Bulletin,
    Classe,
    Eleve,
    Etablissement,
    IncidentDisciplinaire,
    Inscription,
    Trimestre,
)
from app.services.academic_calculation_service import RulesResolutionCache
from app.services.academic_results import (
    build_rulesets_snapshot,
    ensure_student_period_results,
    results_to_moyenne_rows,
)
from app.services.calcul_moyennes import (
    calculer_moyenne_generale,
    calculer_rangs,
    determiner_mention,
)
from app.services.pdf_render import html_to_pdf
from app.services.tenant import (
    apply_tenant_school,
    assert_same_school,
    get_current_school_id,
    get_or_404_tenant,
    tenant_query,
)
from app.utils.audit_logger import log_audit


def _get_trimestre_or_404(db, id_trimestre):
    """Trimestre parent-only : isolation via AnneeScolaire.school_id."""
    trim = (
        db.query(Trimestre)
        .join(AnneeScolaire, AnneeScolaire.id == Trimestre.id_annee)
        .filter(Trimestre.id == id_trimestre, AnneeScolaire.school_id == get_current_school_id())
        .first()
    )
    if not trim:
        abort(404)
    return trim


def _get_moyennes_eleve(db, id_eleve, id_classe, id_trimestre, cache=None):
    """Moyennes matière depuis résultats persistés (PR #13 / PR15-C).

    Recalcule et persiste si absents ou stale. Source unique = store
    AcademicSubjectResult (Calculation Engine). Incomplete → moyenne None.
    """
    if id_classe is None:
        return [], []
    cache = cache or RulesResolutionCache()
    rows = ensure_student_period_results(
        db,
        id_eleve=id_eleve,
        id_classe=id_classe,
        id_period=id_trimestre,
        cache=cache,
    )
    return results_to_moyenne_rows(db, rows), rows


def _appreciation_discipline(db, id_eleve, id_trimestre) -> str | None:
    """Synthèse des incidents disciplinaires du trimestre pour le bulletin."""
    incidents = (
        tenant_query(IncidentDisciplinaire)
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

    eleve = get_or_404_tenant(Eleve, id_eleve)
    trimestre = _get_trimestre_or_404(db, id_trimestre)

    inscription = (
        tenant_query(Inscription)
        .filter(Inscription.id_eleve == id_eleve, Inscription.id_annee == trimestre.id_annee)
        .first()
    )
    if not inscription:
        raise ValueError("Inscription introuvable pour cet élève")
    assert_same_school(eleve, inscription)

    id_classe = inscription.id_classe
    cache = RulesResolutionCache()
    moyennes_mat, result_rows = _get_moyennes_eleve(db, id_eleve, id_classe, id_trimestre, cache=cache)
    # Moyenne générale : exclut déjà les matières incomplete (moyenne None)
    moy_gen = calculer_moyenne_generale(
        [{"moyenne": m["moyenne"], "coefficient_matiere": m["coefficient"]} for m in moyennes_mat]
    )

    # Moyennes de toute la classe pour rang et moyenne classe
    inscriptions_classe = tenant_query(Inscription).filter(Inscription.id_classe == id_classe).all()
    moyennes_classe = {}
    for ins in inscriptions_classe:
        mats, _rows = _get_moyennes_eleve(db, ins.id_eleve, id_classe, id_trimestre, cache=cache)
        mg = calculer_moyenne_generale(
            [{"moyenne": m["moyenne"], "coefficient_matiere": m["coefficient"]} for m in mats]
        )
        moyennes_classe[ins.id_eleve] = mg

    rangs = calculer_rangs(moyennes_classe)
    moyennes_valides = [m for m in moyennes_classe.values() if m is not None]
    moy_classe = sum(moyennes_valides) / len(moyennes_valides) if moyennes_valides else None

    bulletin = (
        tenant_query(Bulletin)
        .filter(Bulletin.id_eleve == id_eleve, Bulletin.id_trimestre == id_trimestre)
        .first()
    )

    if bulletin and bulletin.statut == "publie":
        raise ValueError("Bulletin publié — lecture seule")

    if not bulletin:
        bulletin = Bulletin(
            id=uuid.uuid4(),
            id_eleve=id_eleve,
            id_trimestre=id_trimestre,
        )
        apply_tenant_school(bulletin)
        assert_same_school(eleve, bulletin)
        db.add(bulletin)

    bulletin.moyenne_generale = moy_gen
    bulletin.rang = rangs.get(id_eleve)
    bulletin.effectif_classe = len(inscriptions_classe)
    bulletin.moyenne_classe = round(moy_classe, 2) if moy_classe else None
    bulletin.mention = determiner_mention(moy_gen)
    bulletin.statut = bulletin.statut or "brouillon"
    bulletin.rulesets_snapshot = build_rulesets_snapshot(result_rows)
    bulletin.results_calculated_at = datetime.now(UTC)
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
    assert_same_school(bulletin)
    eleve = get_or_404_tenant(Eleve, bulletin.id_eleve)
    trimestre = _get_trimestre_or_404(db, bulletin.id_trimestre)
    etablissement = (
        db.query(Etablissement).filter(Etablissement.school_id == get_current_school_id()).first()
    )

    annee = tenant_query(AnneeScolaire).filter(AnneeScolaire.id == trimestre.id_annee).first()

    inscription = (
        tenant_query(Inscription)
        .filter(Inscription.id_eleve == bulletin.id_eleve, Inscription.id_annee == trimestre.id_annee)
        .first()
    )
    classe = (
        tenant_query(Classe).filter(Classe.id == inscription.id_classe).first() if inscription else None
    )
    moyennes, _rows = _get_moyennes_eleve(
        db, bulletin.id_eleve, classe.id if classe else None, bulletin.id_trimestre
    )

    html = render_template(
        "bulletin.html",
        etablissement=etablissement,
        eleve=eleve,
        trimestre=trimestre,
        annee=annee,
        classe=classe,
        bulletin=bulletin,
        moyennes=moyennes,
        date_generation=datetime.now(UTC),
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
    bulletin = get_or_404_tenant(Bulletin, bulletin_id)
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
    bulletin = get_or_404_tenant(Bulletin, bulletin_id)
    if bulletin.statut != "valide":
        raise ValueError("Le bulletin doit être validé avant publication")
    generer_bulletin_pdf(bulletin)
    bulletin.statut = "publie"
    db.commit()
    log_audit("PUBLICATION_BULLETIN", id_utilisateur, "bulletin", bulletin.id)

    from app.services.envoi_notification import creer_notification

    eleve = get_or_404_tenant(Eleve, bulletin.id_eleve)
    trimestre = _get_trimestre_or_404(db, bulletin.id_trimestre)
    if eleve and trimestre:
        creer_notification(
            "email",
            "publication_bulletin",
            f"Le bulletin du trimestre {trimestre.numero} de {eleve.prenom} {eleve.nom} est disponible.",
            id_eleve=bulletin.id_eleve,
        )

    return bulletin
