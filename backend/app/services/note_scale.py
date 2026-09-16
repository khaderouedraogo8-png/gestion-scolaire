"""PR #16 — résolution de l'échelle de notation pour une évaluation.

Source de vérité : ResolvedGradingRules.scale_max via Rules Resolution Engine.
Sans ruleset ACTIVE → DEFAULT_SCALE_MAX (constante produit existante).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.models.etablissement import AcademicPeriod, Classe
from app.models.grading import DEFAULT_SCALE_MAX
from app.models.pedagogie import Evaluation
from app.services.academic_calculation_service import (
    RulesResolutionCache,
    build_resolution_context_for_classe,
)
from app.services.grading_rules import (
    GradingContextError,
    GradingRulesConflictError,
    GradingRulesInvalidError,
    GradingRulesNotFoundError,
)
from app.services.tenant import get_or_404_tenant
from app.utils.errors import abort_api


def resolve_scale_max_for_evaluation(
    db: Session,
    evaluation: Evaluation,
    *,
    cache: RulesResolutionCache | None = None,
) -> Decimal:
    """Retourne scale_max applicable à l'évaluation (ruleset résolu ou défaut)."""
    cache = cache or RulesResolutionCache()
    classe = get_or_404_tenant(Classe, evaluation.id_classe)
    period = get_or_404_tenant(AcademicPeriod, evaluation.id_trimestre)
    try:
        ctx = build_resolution_context_for_classe(
            db,
            classe=classe,
            period=period,
            subject_id=evaluation.id_matiere,
        )
        rules = cache.get_or_resolve(db, ctx)
        return Decimal(str(rules.scale_max)).quantize(Decimal("0.01"))
    except (
        GradingRulesNotFoundError,
        GradingRulesConflictError,
        GradingContextError,
        GradingRulesInvalidError,
    ):
        return Decimal(str(DEFAULT_SCALE_MAX)).quantize(Decimal("0.01"))


def validate_note_valeur_against_scale(
    valeur,
    *,
    scale_max: Decimal,
    absent: bool = False,
) -> Decimal | None:
    """Valide une note saisie. Absent / None → None (missing ≠ 0).

    Refuse valeur < 0 ou valeur > scale_max.
    """
    if absent:
        return None
    if valeur is None:
        return None
    try:
        dec = Decimal(str(valeur))
    except (InvalidOperation, TypeError, ValueError):
        abort_api(400, "INVALID_GRADE", "valeur_note invalide.")
    if dec < 0:
        abort_api(
            400,
            "GRADE_OUT_OF_SCALE",
            "valeur_note ne peut pas être négative.",
            details={"valeur_note": str(dec), "scale_max": str(scale_max)},
        )
    if dec > scale_max:
        abort_api(
            400,
            "GRADE_OUT_OF_SCALE",
            f"valeur_note ({dec}) dépasse l'échelle maximale ({scale_max}).",
            details={"valeur_note": str(dec), "scale_max": str(scale_max)},
        )
    return dec
