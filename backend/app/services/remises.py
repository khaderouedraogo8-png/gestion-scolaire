"""Moteur de remises scolaires (fratrie, bourse, manuelle)."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import EleveFratrie, Inscription, RemiseRegle


def _as_decimal(value) -> Decimal:
    if value is None:
        return Decimal(0)
    return Decimal(str(value))


def _count_fratrie(db: Session, eleve_id: uuid.UUID, school_id: uuid.UUID) -> int:
    link = (
        db.query(EleveFratrie)
        .filter(
            EleveFratrie.id_eleve == eleve_id,
            EleveFratrie.school_id == school_id,
        )
        .first()
    )
    if not link:
        return 1
    return (
        db.query(EleveFratrie)
        .filter(
            EleveFratrie.id_fratrie == link.id_fratrie,
            EleveFratrie.school_id == school_id,
        )
        .count()
    )


def _active_inscription(
    db: Session, eleve_id: uuid.UUID, school_id: uuid.UUID
) -> Inscription | None:
    return (
        db.query(Inscription)
        .filter(
            Inscription.id_eleve == eleve_id,
            Inscription.school_id == school_id,
            Inscription.statut.in_(("inscrit", "reinscrit")),
        )
        .order_by(Inscription.date_inscription.desc())
        .first()
    )


def compute_remise_eleve(
    db: Session,
    eleve_id: uuid.UUID,
    school_id: uuid.UUID,
) -> dict:
    """Calcule le cumul de remises applicables à un élève.

    Returns:
        {taux_percent, montant_fixe, sources[]}
    """
    sources: list[dict] = []
    taux_percent = Decimal(0)
    montant_fixe = Decimal(0)

    insc = _active_inscription(db, eleve_id, school_id)
    fratrie_count = _count_fratrie(db, eleve_id, school_id)

    regles = (
        db.query(RemiseRegle)
        .filter(
            RemiseRegle.school_id == school_id,
            RemiseRegle.actif.is_(True),
        )
        .order_by(RemiseRegle.priorite.desc(), RemiseRegle.created_at.asc())
        .all()
    )

    for regle in regles:
        ctype = (regle.condition_type or "").strip().lower()
        applicable = False
        detail: dict = {
            "id_regle": str(regle.id),
            "code": regle.code,
            "libelle": regle.libelle,
            "condition_type": ctype or None,
            "type_remise": regle.type_remise,
            "valeur": float(regle.valeur),
        }

        if ctype == "fratrie":
            try:
                min_count = int(regle.condition_valeur or "2")
            except (TypeError, ValueError):
                min_count = 2
            if fratrie_count >= min_count:
                applicable = True
                detail["fratrie_count"] = fratrie_count
                detail["seuil"] = min_count
        elif ctype == "bourse":
            if insc and insc.est_boursier:
                applicable = True
                detail["est_boursier"] = True
        elif ctype == "manuelle":
            # Règle manuelle explicite — appliquée si inscription a un taux, sinon valeur règle
            if insc and float(insc.taux_reduction or 0) > 0 or regle.type_remise == "montant" and _as_decimal(regle.valeur) > 0:
                applicable = True

        if not applicable:
            continue

        if regle.type_remise == "montant":
            montant_fixe += _as_decimal(regle.valeur)
            detail["contribution"] = {"montant_fixe": float(regle.valeur)}
        else:
            taux_percent += _as_decimal(regle.valeur)
            detail["contribution"] = {"taux_percent": float(regle.valeur)}
        sources.append(detail)

    # Remise manuelle inscription.taux_reduction (hors règle RemiseRegle)
    if insc and float(insc.taux_reduction or 0) > 0:
        already_manual = any(
            s.get("condition_type") == "manuelle" and s.get("code") == "INSCRIPTION_TAUX"
            for s in sources
        )
        # Éviter double-comptage si une règle manuelle a déjà repris le même taux
        covered_by_regle = any(
            s.get("condition_type") == "manuelle"
            and s.get("type_remise") == "pourcent"
            and abs(float(s.get("valeur") or 0) - float(insc.taux_reduction)) < 0.01
            for s in sources
        )
        if not already_manual and not covered_by_regle:
            taux = _as_decimal(insc.taux_reduction)
            taux_percent += taux
            sources.append({
                "code": "INSCRIPTION_TAUX",
                "libelle": "Remise manuelle (inscription)",
                "condition_type": "manuelle",
                "type_remise": "pourcent",
                "valeur": float(taux),
                "contribution": {"taux_percent": float(taux)},
            })

    taux_percent = min(taux_percent, Decimal(100))

    return {
        "taux_percent": float(taux_percent.quantize(Decimal("0.01"))),
        "montant_fixe": float(montant_fixe.quantize(Decimal("0.01"))),
        "sources": sources,
        "fratrie_count": fratrie_count,
        "est_boursier": bool(insc.est_boursier) if insc else False,
        "taux_reduction_inscription": float(insc.taux_reduction or 0) if insc else 0.0,
    }


def apply_remise_to_montant(montant: float | Decimal, remise: dict | None) -> float:
    """Applique taux % puis montant fixe ; résultat >= 0."""
    base = _as_decimal(montant)
    if not remise:
        return float(base.quantize(Decimal("0.01")))
    taux = _as_decimal(remise.get("taux_percent") or 0)
    fixe = _as_decimal(remise.get("montant_fixe") or 0)
    net = base * (Decimal(1) - taux / Decimal(100)) - fixe
    if net < 0:
        net = Decimal(0)
    return float(net.quantize(Decimal("0.01")))


def get_remise_cached(
    db: Session,
    eleve_id: uuid.UUID,
    school_id: uuid.UUID,
    cache: dict | None = None,
) -> dict:
    """compute_remise_eleve avec cache optionnel par élève."""
    key = str(eleve_id)
    if cache is not None and key in cache:
        return cache[key]
    result = compute_remise_eleve(db, eleve_id, school_id)
    if cache is not None:
        cache[key] = result
    return result
