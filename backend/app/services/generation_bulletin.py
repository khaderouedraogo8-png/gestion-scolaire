"""Génération de bulletins PDF via WeasyPrint."""
import os
import uuid
from datetime import UTC, datetime

from flask import abort, current_app, render_template
from sqlalchemy import text

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
from app.services.calcul_moyennes import (
    calculer_moyenne_generale,
    calculer_rangs,
    determiner_mention,
    refresh_moyenne_matiere_view,
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


def _get_moyennes_eleve(db, id_eleve, id_classe, id_trimestre):
    """Moyennes matière : Rules Engine (Step 4) si ruleset ACTIVE, sinon vue legacy.

    Ne recalcule pas les PDF — fournit les lignes consommées par le bulletin.
    """
    from app.services.academic_calculation_service import (
        RulesResolutionCache,
        calculate_student_period_results,
        subject_results_to_moyenne_rows,
    )
    from app.services.grading_rules import GradingContextError, GradingRulesConflictError

    school_id = get_current_school_id()
    legacy_rows = db.execute(
        text("""
            SELECT m.id_matiere, mat.libelle, m.moyenne, cm.coefficient
            FROM moyenne_matiere_eleve m
            JOIN matiere mat ON mat.id = m.id_matiere
            LEFT JOIN classe c ON c.id = m.id_classe
            LEFT JOIN coefficient_matiere cm ON cm.id_matiere = m.id_matiere
                AND cm.id_niveau = c.id_niveau
            WHERE m.id_eleve = :id_eleve AND m.id_trimestre = :id_trimestre
                AND mat.school_id = :school_id
        """),
        {"id_eleve": id_eleve, "id_trimestre": id_trimestre, "school_id": school_id},
    ).fetchall()
    legacy_by_matiere = {
        r[0]: {
            "id_matiere": r[0],
            "libelle": r[1],
            "moyenne": float(r[2]) if r[2] is not None else None,
            "coefficient": float(r[3]) if r[3] is not None else 1,
        }
        for r in legacy_rows
    }

    try:
        results, _ga, _meta = calculate_student_period_results(
            db,
            id_eleve=id_eleve,
            id_classe=id_classe,
            id_period=id_trimestre,
            cache=RulesResolutionCache(),
            subject_ids=list(legacy_by_matiere.keys()) or None,
        )
    except (GradingRulesConflictError, GradingContextError) as exc:
        # Conflit / contexte invalide : fallback legacy pour ne pas bloquer la génération
        # historique. Visible via resolve API + log warning (Step 6 observabilité).
        current_app.logger.warning(
            "bulletin_moyennes_fallback_legacy eleve=%s classe=%s periode=%s err=%s",
            id_eleve,
            id_classe,
            id_trimestre,
            exc,
        )
        return list(legacy_by_matiere.values())

    engine_rows = subject_results_to_moyenne_rows(db, results)
    engine_by_matiere = {r["id_matiere"]: r for r in engine_rows}

    # Fusion : ruleset gagne ; matières sans ruleset → legacy (vue)
    merged = []
    seen = set()
    for mid, row in legacy_by_matiere.items():
        seen.add(mid)
        if mid in engine_by_matiere:
            eng = engine_by_matiere[mid]
            merged.append(
                {
                    "id_matiere": mid,
                    "libelle": row["libelle"],
                    "moyenne": eng["moyenne"],
                    "coefficient": eng["coefficient"],
                    "ruleset_id": eng.get("ruleset_id"),
                    "ruleset_version": eng.get("ruleset_version"),
                }
            )
        else:
            merged.append(row)
    for mid, eng in engine_by_matiere.items():
        if mid not in seen:
            merged.append(
                {
                    "id_matiere": mid,
                    "libelle": eng.get("libelle"),
                    "moyenne": eng["moyenne"],
                    "coefficient": eng["coefficient"],
                    "ruleset_id": eng.get("ruleset_id"),
                    "ruleset_version": eng.get("ruleset_version"),
                }
            )
    return merged


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
    refresh_moyenne_matiere_view(db)

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
    moyennes_mat = _get_moyennes_eleve(db, id_eleve, id_classe, id_trimestre)
    moy_gen = calculer_moyenne_generale(
        [{"moyenne": m["moyenne"], "coefficient_matiere": m["coefficient"]} for m in moyennes_mat]
    )

    # Moyennes de toute la classe pour rang et moyenne classe
    inscriptions_classe = tenant_query(Inscription).filter(Inscription.id_classe == id_classe).all()
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
