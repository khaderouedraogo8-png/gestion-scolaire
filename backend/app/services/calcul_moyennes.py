"""Calcul des moyennes — absent != note 0."""
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal


def calculer_moyenne_matiere(notes: list[dict]) -> float | None:
    """
    Moyenne matière = Σ(note × coef) / Σ(coef).
    Les absences sont exclues du calcul (absent != 0).
    Chaque note : {"valeur": float, "coefficient": float, "absent": bool}
    """
    total_pondere = Decimal(0)
    total_coef = Decimal(0)
    for n in notes:
        if n.get("absent"):
            continue
        if n.get("valeur") is None:
            continue
        coef = Decimal(str(n["coefficient"]))
        total_pondere += Decimal(str(n["valeur"])) * coef
        total_coef += coef
    if total_coef == 0:
        return None
    moyenne = total_pondere / total_coef
    return float(moyenne.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculer_moyenne_generale(moyennes_matieres: list[dict]) -> float | None:
    """
    Moyenne générale = Σ(moyenne matière × coef matière) / Σ(coef matière).
    Chaque entrée : {"moyenne": float, "coefficient_matiere": float}
    """
    total_pondere = Decimal(0)
    total_coef = Decimal(0)
    for m in moyennes_matieres:
        if m.get("moyenne") is None:
            continue
        coef = Decimal(str(m["coefficient_matiere"]))
        total_pondere += Decimal(str(m["moyenne"])) * coef
        total_coef += coef
    if total_coef == 0:
        return None
    moyenne = total_pondere / total_coef
    return float(moyenne.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculer_rangs(moyennes_eleves: dict) -> dict:
    """
    Calcule le rang de chaque élève.
    moyennes_eleves : {id_eleve: moyenne_generale}
    Retourne {id_eleve: rang}
    """
    sorted_eleves = sorted(
        moyennes_eleves.items(),
        key=lambda x: (x[1] is not None, x[1] or 0),
        reverse=True,
    )
    rangs = {}
    rang = 0
    prev_moyenne = None
    for i, (id_eleve, moyenne) in enumerate(sorted_eleves):
        if moyenne is None:
            rangs[id_eleve] = None
            continue
        if moyenne != prev_moyenne:
            rang = i + 1
        rangs[id_eleve] = rang
        prev_moyenne = moyenne
    return rangs


def determiner_mention(moyenne: float | None) -> str | None:
    """Détermine la mention selon la moyenne générale."""
    if moyenne is None:
        return None
    if moyenne >= 16:
        return "Très Bien"
    if moyenne >= 14:
        return "Bien"
    if moyenne >= 12:
        return "Assez Bien"
    if moyenne >= 10:
        return "Passable"
    return "Insuffisant"


def agreger_notes_par_matiere(notes_evaluation: list[dict]) -> dict:
    """
    Agrège les notes par matière pour un élève.
    Retourne {id_matiere: [notes]}
    """
    par_matiere = defaultdict(list)
    for n in notes_evaluation:
        par_matiere[n["id_matiere"]].append(n)
    return dict(par_matiere)


def refresh_moyenne_matiere_view(db_session) -> None:
    """Rafraîchit la vue matérialisée moyenne_matiere_eleve."""
    from sqlalchemy import text

    db_session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY moyenne_matiere_eleve"))
    db_session.commit()
