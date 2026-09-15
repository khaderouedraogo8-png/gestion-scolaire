"""PR #12 Step 4 — Academic Calculation Engine.

Applique ``ResolvedGradingRules`` (Step 2) aux notes pour produire une moyenne matière.
Ne résout PAS les rulesets (délègue à ``resolve_grading_rules``).
Ne connaît PAS les bulletins / PDF / templates.

Sémantique V1 documentée :
- Agrégation par ``evaluation_type_code`` (moyenne arithmétique des notes du type).
- Pondération via ``component.weight`` (pourcentage / 100) — jamais hardcodée.
- ``absent`` / ``valeur is None`` exclus (missing ≠ 0) ; ``valeur=0`` compte.
- Composante ``is_required`` sans note utilisable → moyenne matière = None.
- Composante optionnelle manquante → omise ; renormalisation sur poids présents.
- Coefficient matière appliqué APRÈS la moyenne matière (weighted_score).
- Un seul arrondi final sur la moyenne matière (mode/précision du ruleset).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import (
    ROUND_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Decimal,
    InvalidOperation,
)
from typing import Any

from app.models.grading import (
    GRADING_ROUNDING_DOWN,
    GRADING_ROUNDING_HALF_EVEN,
    GRADING_ROUNDING_HALF_UP,
    GRADING_ROUNDING_UP,
    WEIGHT_PERCENT_SCALE,
)
from app.services.grading_rules import ResolvedComponent, ResolvedGradingRules

_ROUNDING_MAP = {
    GRADING_ROUNDING_HALF_UP: ROUND_HALF_UP,
    GRADING_ROUNDING_HALF_EVEN: ROUND_HALF_EVEN,
    GRADING_ROUNDING_DOWN: ROUND_DOWN,
    GRADING_ROUNDING_UP: ROUND_UP,
}

_HUNDRED = WEIGHT_PERCENT_SCALE  # Decimal("100.00")


# ---------------------------------------------------------------------------
# Input / output DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GradeInput:
    """Note brute pour le calculateur (déjà filtrée tenant en amont)."""

    evaluation_id: uuid.UUID
    evaluation_type_code: str
    valeur: Decimal | None
    absent: bool = False
    evaluation_context: str | None = None


@dataclass(slots=True)
class ComponentCalculation:
    component_id: uuid.UUID
    code: str
    label: str
    evaluation_type_code: str
    weight: Decimal
    is_required: bool
    grade_values: list[Decimal] = field(default_factory=list)
    component_average: Decimal | None = None
    missing: bool = True
    contribution: Decimal | None = None  # average × (weight/100) avant renormalisation


@dataclass(slots=True)
class SubjectResult:
    subject_id: uuid.UUID | None
    subject_average: Decimal | None
    scale_max: Decimal
    coefficient: Decimal
    weighted_score: Decimal | None  # subject_average × coefficient (si moyenne définie)
    ruleset_id: uuid.UUID
    ruleset_code: str
    ruleset_version: int
    rounding_mode: str
    rounding_precision: int
    components: list[ComponentCalculation] = field(default_factory=list)
    incomplete: bool = False
    incomplete_reason: str | None = None
    calculation_trace: list[str] = field(default_factory=list)

    def as_float_average(self) -> float | None:
        if self.subject_average is None:
            return None
        return float(self.subject_average)


@dataclass(slots=True)
class GeneralAverageResult:
    average: Decimal | None
    subjects_counted: int
    total_coefficient: Decimal
    calculation_trace: list[str] = field(default_factory=list)

    def as_float(self) -> float | None:
        if self.average is None:
            return None
        return float(self.average)


# ---------------------------------------------------------------------------
# Rounding
# ---------------------------------------------------------------------------


def decimal_rounding_mode(mode: str):
    key = (mode or GRADING_ROUNDING_HALF_UP).strip().lower()
    if key not in _ROUNDING_MAP:
        raise ValueError(f"rounding_mode inconnu : {mode}")
    return _ROUNDING_MAP[key]


def apply_rounding(value: Decimal, *, mode: str, precision: int) -> Decimal:
    """Arrondi déterministe unique — quantize Decimal (pas float)."""
    if precision < 0:
        raise ValueError("rounding_precision doit être ≥ 0")
    quant = Decimal(1).scaleb(-precision) if precision else Decimal(1)
    return value.quantize(quant, rounding=decimal_rounding_mode(mode))


def _as_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Valeur numérique invalide : {value!r}") from exc


# ---------------------------------------------------------------------------
# Subject calculation (pure)
# ---------------------------------------------------------------------------


def _usable_grade(g: GradeInput) -> Decimal | None:
    """missing ≠ 0 : absent ou None exclus ; zéro explicite conservé."""
    if g.absent:
        return None
    if g.valeur is None:
        return None
    return _as_decimal(g.valeur)


def _group_grades_by_type(grades: list[GradeInput]) -> dict[str, list[Decimal]]:
    grouped: dict[str, list[Decimal]] = {}
    for g in grades:
        code = (g.evaluation_type_code or "").strip().lower()
        val = _usable_grade(g)
        if val is None:
            continue
        grouped.setdefault(code, []).append(val)
    return grouped


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / Decimal(len(values))


def calculate_subject_result(
    grades: list[GradeInput],
    rules: ResolvedGradingRules,
    *,
    subject_id: uuid.UUID | None = None,
    subject_coefficient: Decimal | float | str = Decimal(1),
) -> SubjectResult:
    """Calcule la moyenne matière à partir des règles résolues.

    Étape 1 : notes → moyenne par type d'évaluation (composante).
    Étape 2 : composantes × poids → moyenne matière (un arrondi final).
    """
    coef = _as_decimal(subject_coefficient)
    if coef < 0:
        raise ValueError("coefficient matière ne peut pas être négatif")

    grouped = _group_grades_by_type(grades)
    components_out: list[ComponentCalculation] = []
    trace: list[str] = [
        (
            f"Ruleset {rules.ruleset_code} v{rules.ruleset_version} "
            f"(id={rules.ruleset_id}, scale_max={rules.scale_max}, "
            f"round={rules.rounding_mode}/{rules.rounding_precision})"
        )
    ]

    present_weight_sum = Decimal("0.00")
    weighted_sum = Decimal("0.00")
    missing_required: list[str] = []

    for comp in sorted(rules.components, key=lambda c: c.sequence):
        type_code = (comp.evaluation_type_code or "").strip().lower()
        values = list(grouped.get(type_code, []))
        calc = ComponentCalculation(
            component_id=comp.id,
            code=comp.code,
            label=comp.label,
            evaluation_type_code=type_code,
            weight=_as_decimal(comp.weight),
            is_required=comp.is_required,
            grade_values=values,
        )
        if not values:
            calc.missing = True
            calc.component_average = None
            calc.contribution = None
            if comp.is_required:
                missing_required.append(comp.code)
            trace.append(
                f"Composante {comp.code} ({type_code}, poids={comp.weight}%) : "
                f"{'REQUISE manquante' if comp.is_required else 'optionnelle manquante'} — ignorée"
            )
        else:
            avg = _mean(values)
            calc.missing = False
            calc.component_average = avg  # non arrondi — arrondi final uniquement
            weight_factor = calc.weight / _HUNDRED
            calc.contribution = avg * weight_factor
            present_weight_sum += calc.weight
            weighted_sum += calc.contribution
            vals_str = ", ".join(str(v) for v in values)
            trace.append(
                f"Composante {comp.code} ({type_code}): [{vals_str}] "
                f"→ moyenne={avg} × {calc.weight}% = {calc.contribution}"
            )
        components_out.append(calc)

    if missing_required:
        reason = (
            "Composantes requises sans note utilisable : " + ", ".join(missing_required)
        )
        trace.append(f"INCOMPLET — {reason}")
        return SubjectResult(
            subject_id=subject_id,
            subject_average=None,
            scale_max=_as_decimal(rules.scale_max),
            coefficient=coef,
            weighted_score=None,
            ruleset_id=rules.ruleset_id,
            ruleset_code=rules.ruleset_code,
            ruleset_version=rules.ruleset_version,
            rounding_mode=rules.rounding_mode,
            rounding_precision=rules.rounding_precision,
            components=components_out,
            incomplete=True,
            incomplete_reason=reason,
            calculation_trace=trace,
        )

    if present_weight_sum <= 0:
        reason = "Aucune composante avec note utilisable."
        trace.append(f"INCOMPLET — {reason}")
        return SubjectResult(
            subject_id=subject_id,
            subject_average=None,
            scale_max=_as_decimal(rules.scale_max),
            coefficient=coef,
            weighted_score=None,
            ruleset_id=rules.ruleset_id,
            ruleset_code=rules.ruleset_code,
            ruleset_version=rules.ruleset_version,
            rounding_mode=rules.rounding_mode,
            rounding_precision=rules.rounding_precision,
            components=components_out,
            incomplete=True,
            incomplete_reason=reason,
            calculation_trace=trace,
        )

    # Renormalisation uniquement si des optionnelles manquent (somme poids présents < 100)
    raw = weighted_sum * _HUNDRED / present_weight_sum
    rounded = apply_rounding(
        raw, mode=rules.rounding_mode, precision=rules.rounding_precision
    )
    if present_weight_sum != _HUNDRED:
        trace.append(
            f"Renormalisation : poids présents={present_weight_sum} "
            f"(brut={raw} → arrondi={rounded})"
        )
    else:
        trace.append(f"Moyenne matière = {raw} → arrondi={rounded}")

    weighted_score = None
    if coef > 0:
        weighted_score = rounded * coef
        trace.append(f"Contribution MG : {rounded} × coef {coef} = {weighted_score}")
    else:
        trace.append(f"Coefficient matière={coef} — exclu de la moyenne générale")

    return SubjectResult(
        subject_id=subject_id,
        subject_average=rounded,
        scale_max=_as_decimal(rules.scale_max),
        coefficient=coef,
        weighted_score=weighted_score,
        ruleset_id=rules.ruleset_id,
        ruleset_code=rules.ruleset_code,
        ruleset_version=rules.ruleset_version,
        rounding_mode=rules.rounding_mode,
        rounding_precision=rules.rounding_precision,
        components=components_out,
        incomplete=False,
        incomplete_reason=None,
        calculation_trace=trace,
    )


def calculate_general_average(
    subject_results: list[SubjectResult],
    *,
    rounding_mode: str = GRADING_ROUNDING_HALF_UP,
    rounding_precision: int = 2,
) -> GeneralAverageResult:
    """Moyenne générale = Σ(moyenne_matière × coef) / Σ(coef), coef > 0, moyenne définie.

    Les matières sans moyenne (None) ou coef ≤ 0 sont exclues (≠ 0).
    Arrondi final unique (paramètres fournis — typiquement défaut école).
    """
    total_pondere = Decimal(0)
    total_coef = Decimal(0)
    counted = 0
    trace: list[str] = []
    for sr in subject_results:
        if sr.subject_average is None:
            trace.append(f"Matière {sr.subject_id}: ignorée (pas de moyenne)")
            continue
        if sr.coefficient <= 0:
            trace.append(f"Matière {sr.subject_id}: ignorée (coef={sr.coefficient})")
            continue
        total_pondere += sr.subject_average * sr.coefficient
        total_coef += sr.coefficient
        counted += 1
        trace.append(
            f"Matière {sr.subject_id}: {sr.subject_average} × {sr.coefficient}"
        )

    if total_coef == 0:
        return GeneralAverageResult(
            average=None,
            subjects_counted=0,
            total_coefficient=Decimal(0),
            calculation_trace=trace + ["Aucune matière contributive"],
        )

    raw = total_pondere / total_coef
    rounded = apply_rounding(raw, mode=rounding_mode, precision=rounding_precision)
    trace.append(f"MG = {raw} → {rounded}")
    return GeneralAverageResult(
        average=rounded,
        subjects_counted=counted,
        total_coefficient=total_coef,
        calculation_trace=trace,
    )


def build_minimal_resolved_rules(
    *,
    components: list[tuple],
    scale_max: Decimal = Decimal("20.00"),
    rounding_mode: str = GRADING_ROUNDING_HALF_UP,
    rounding_precision: int = 2,
    ruleset_id: uuid.UUID | None = None,
    ruleset_code: str = "TEST",
    ruleset_version: int = 1,
    school_id: uuid.UUID | None = None,
) -> ResolvedGradingRules:
    """Helper tests : construit un ResolvedGradingRules minimal sans DB.

    ``components`` = [(code, evaluation_type_code, weight), ...]
    ou [(code, evaluation_type_code, weight, is_required), ...]
    """
    from app.services.grading_rules import ResolutionTrace

    rid = ruleset_id or uuid.uuid4()
    sid = school_id or uuid.uuid4()
    resolved_comps: list[ResolvedComponent] = []
    for i, item in enumerate(components, start=1):
        if len(item) == 4:
            code, type_code, weight, is_required = item
        else:
            code, type_code, weight = item
            is_required = True
        resolved_comps.append(
            ResolvedComponent(
                id=uuid.uuid4(),
                code=code,
                label=code,
                evaluation_type_id=uuid.uuid4(),
                evaluation_type_code=type_code,
                evaluation_context="normal",
                weight=_as_decimal(weight),
                sequence=i,
                is_required=bool(is_required),
            )
        )
    return ResolvedGradingRules(
        ruleset_id=rid,
        ruleset_code=ruleset_code,
        ruleset_version=ruleset_version,
        school_id=sid,
        specificity=0,
        scope_description="test",
        scope_level="school",
        scale_max=_as_decimal(scale_max),
        rounding_mode=rounding_mode,
        rounding_precision=rounding_precision,
        components=resolved_comps,
        trace=ResolutionTrace(),
    )
