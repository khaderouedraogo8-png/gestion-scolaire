"""PR #12 Step 2 — Rules Resolution Engine (lecture seule, déterministe).

Ne calcule aucune note / moyenne / rang. Ne modifie aucune entité.
Sélectionne le GradingRuleset ACTIVE le plus spécifique, ou lève un conflit.

Scopes V1 (modèle Step 1) : School × Year × Program? × Level? × Subject?
Class et AcademicPeriod font partie du *contexte* (validation de cohérence) mais
ne sont pas des axes de matching V1 (pas de colonnes sur grading_ruleset).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.models.etablissement import AcademicPeriod, AnneeScolaire, Classe, NiveauEtude, Program
from app.models.grading import (
    GRADING_RULESET_STATUS_ACTIVE,
    WEIGHT_PERCENT_SCALE,
    EvaluationType,
    GradingRuleComponent,
    GradingRuleset,
)
from app.models.pedagogie import Matiere
from app.models.school import School

# ---------------------------------------------------------------------------
# Specificity — explicite, testable, indépendante de l'ordre SQL
# Axes V1 représentables : program / level / subject (year+school toujours)
# ---------------------------------------------------------------------------

SPEC_SUBJECT = 100
SPEC_LEVEL = 10
SPEC_PROGRAM = 1

# Hiérarchie résultante (score décroissant) :
# program+level+subject = 111
# level+subject         = 110  (niveau implique program en DB)
# program+subject       = 101
# subject               = 100
# program+level         = 011
# level                 = 010  (invalide en DB sans program — score théorique)
# program               = 001
# school/year default   = 000


# ---------------------------------------------------------------------------
# Exceptions métier
# ---------------------------------------------------------------------------


class GradingRulesError(Exception):
    """Erreur de base du moteur de règles de notation."""

    code: str = "GRADING_RULES_ERROR"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class GradingContextError(GradingRulesError):
    """Contexte académique invalide ou cross-tenant."""

    code = "TENANT_CONTEXT_ERROR"


class GradingRulesNotFoundError(GradingRulesError):
    """Aucun ruleset ACTIVE applicable."""

    code = "NO_RULESET"


class GradingRulesConflictError(GradingRulesError):
    """Plusieurs rulesets ACTIVE de même spécificité."""

    code = "RULESET_CONFLICT"


class GradingRulesInvalidError(GradingRulesError):
    """Ruleset structurellement inutilisable (poids, composants)."""

    code = "RULESET_INVALID"


# ---------------------------------------------------------------------------
# Context / result DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ResolutionContext:
    """Contexte académique pour résoudre un ruleset.

    ``program_id`` est requis (toute classe/période PR11 est rattachée à un programme).
    ``class_id`` / ``academic_period_id`` servent à la validation de cohérence ;
    ils n'entrent pas dans le matching V1 (pas d'axes Class/Period sur le ruleset).
    """

    school_id: uuid.UUID
    academic_year_id: uuid.UUID
    program_id: uuid.UUID
    level_id: uuid.UUID | None = None
    class_id: uuid.UUID | None = None
    subject_id: uuid.UUID | None = None
    academic_period_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class ResolvedComponent:
    id: uuid.UUID
    code: str
    label: str
    evaluation_type_id: uuid.UUID
    evaluation_type_code: str
    evaluation_context: str
    weight: Decimal
    sequence: int
    is_required: bool


@dataclass(frozen=True, slots=True)
class ResolutionCandidate:
    ruleset_id: uuid.UUID
    code: str
    version: int
    status: str
    specificity: int
    scope_description: str
    id_program: uuid.UUID | None
    id_niveau: uuid.UUID | None
    id_matiere: uuid.UUID | None


@dataclass(slots=True)
class ResolutionTrace:
    """Trace de diagnostic — non persistée."""

    candidates: list[ResolutionCandidate] = field(default_factory=list)
    selected: ResolutionCandidate | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResolvedGradingRules:
    ruleset_id: uuid.UUID
    ruleset_code: str
    ruleset_version: int
    school_id: uuid.UUID
    specificity: int
    scope_description: str
    scope_level: str
    scale_max: Decimal
    rounding_mode: str
    rounding_precision: int
    components: list[ResolvedComponent]
    trace: ResolutionTrace


# ---------------------------------------------------------------------------
# Specificity helpers (purs — unit-testables sans DB)
# ---------------------------------------------------------------------------


def specificity_score(
    *,
    id_program: uuid.UUID | None,
    id_niveau: uuid.UUID | None,
    id_matiere: uuid.UUID | None,
) -> int:
    """Score de spécificité V1. Plus élevé = plus prioritaire."""
    score = 0
    if id_matiere is not None:
        score += SPEC_SUBJECT
    if id_niveau is not None:
        score += SPEC_LEVEL
    if id_program is not None:
        score += SPEC_PROGRAM
    return score


def specificity_score_for_ruleset(ruleset: GradingRuleset) -> int:
    return specificity_score(
        id_program=ruleset.id_program,
        id_niveau=ruleset.id_niveau,
        id_matiere=ruleset.id_matiere,
    )


def scope_description_for(
    *,
    id_program: uuid.UUID | None,
    id_niveau: uuid.UUID | None,
    id_matiere: uuid.UUID | None,
) -> str:
    parts = ["school", "year"]
    if id_program is not None:
        parts.append("program")
    if id_niveau is not None:
        parts.append("level")
    if id_matiere is not None:
        parts.append("subject")
    return "+".join(parts)


def scope_level_label(score: int) -> str:
    """Libellé stable pour le résultat (pas pour le tri)."""
    mapping = {
        SPEC_SUBJECT + SPEC_LEVEL + SPEC_PROGRAM: "program+level+subject",
        SPEC_SUBJECT + SPEC_LEVEL: "level+subject",
        SPEC_SUBJECT + SPEC_PROGRAM: "program+subject",
        SPEC_SUBJECT: "subject",
        SPEC_LEVEL + SPEC_PROGRAM: "program+level",
        SPEC_LEVEL: "level",
        SPEC_PROGRAM: "program",
        0: "school",
    }
    return mapping.get(score, f"score:{score}")


# ---------------------------------------------------------------------------
# Component weight validation (réutilisable Step 3 API)
# ---------------------------------------------------------------------------


def validate_component_weights(
    components: list[GradingRuleComponent] | list[ResolvedComponent],
    *,
    expected_total: Decimal = WEIGHT_PERCENT_SCALE,
) -> Decimal:
    """Vérifie weight > 0 (déjà en DB) et somme exacte = expected_total (100.00 %)."""
    if not components:
        raise GradingRulesInvalidError(
            "Ruleset sans composantes — configuration inutilisable.",
            details={"component_count": 0},
        )
    total = sum((Decimal(str(c.weight)) for c in components), Decimal("0.00"))
    if total != expected_total:
        raise GradingRulesInvalidError(
            f"Somme des poids invalide : {total} (attendu {expected_total}).",
            details={
                "weight_sum": str(total),
                "expected_total": str(expected_total),
                "component_count": len(components),
            },
        )
    return total


# ---------------------------------------------------------------------------
# Context validation
# ---------------------------------------------------------------------------


def _require_entity[T](
    db: Session,
    model: type[T],
    entity_id: uuid.UUID,
    *,
    school_id: uuid.UUID,
    label: str,
) -> T:
    obj = db.query(model).filter(model.id == entity_id).first()  # type: ignore[attr-defined]
    if obj is None:
        raise GradingContextError(
            f"{label} introuvable.",
            details={"entity": label, "id": str(entity_id), "code": "NOT_FOUND"},
        )
    entity_school = getattr(obj, "school_id", None)
    if entity_school is not None and entity_school != school_id:
        raise GradingContextError(
            f"{label} n'appartient pas à l'école du contexte (cross-tenant).",
            details={
                "entity": label,
                "id": str(entity_id),
                "entity_school_id": str(entity_school),
                "context_school_id": str(school_id),
                "code": "TENANT_CONTEXT_ERROR",
            },
        )
    return obj


def validate_resolution_context(db: Session, ctx: ResolutionContext) -> None:
    """Valide tenant + cohérence académique PR11. N'est PAS un « no ruleset »."""
    _require_entity(db, School, ctx.school_id, school_id=ctx.school_id, label="School")

    year = _require_entity(
        db, AnneeScolaire, ctx.academic_year_id, school_id=ctx.school_id, label="AcademicYear"
    )
    if year.school_id != ctx.school_id:
        raise GradingContextError("Année scolaire hors tenant.")

    program = _require_entity(
        db, Program, ctx.program_id, school_id=ctx.school_id, label="Program"
    )
    if program.school_id != ctx.school_id:
        raise GradingContextError("Programme hors tenant.")

    level: NiveauEtude | None = None
    if ctx.level_id is not None:
        level = _require_entity(
            db, NiveauEtude, ctx.level_id, school_id=ctx.school_id, label="Level"
        )
        if level.id_program != ctx.program_id:
            raise GradingContextError(
                "Niveau incohérent avec le programme du contexte.",
                details={
                    "level_id": str(ctx.level_id),
                    "level_program_id": str(level.id_program),
                    "context_program_id": str(ctx.program_id),
                    "code": "ACADEMIC_INCONSISTENCY",
                },
            )

    if ctx.class_id is not None:
        classe = _require_entity(
            db, Classe, ctx.class_id, school_id=ctx.school_id, label="Class"
        )
        if classe.id_annee != ctx.academic_year_id:
            raise GradingContextError(
                "Classe incohérente avec l'année du contexte.",
                details={"code": "ACADEMIC_INCONSISTENCY"},
            )
        if classe.id_program != ctx.program_id:
            raise GradingContextError(
                "Classe incohérente avec le programme du contexte.",
                details={"code": "ACADEMIC_INCONSISTENCY"},
            )
        if ctx.level_id is not None and classe.id_niveau != ctx.level_id:
            raise GradingContextError(
                "Classe incohérente avec le niveau du contexte.",
                details={
                    "class_level_id": str(classe.id_niveau),
                    "context_level_id": str(ctx.level_id),
                    "code": "ACADEMIC_INCONSISTENCY",
                },
            )

    if ctx.subject_id is not None:
        _require_entity(db, Matiere, ctx.subject_id, school_id=ctx.school_id, label="Subject")

    if ctx.academic_period_id is not None:
        period = _require_entity(
            db,
            AcademicPeriod,
            ctx.academic_period_id,
            school_id=ctx.school_id,
            label="AcademicPeriod",
        )
        if period.id_annee != ctx.academic_year_id:
            raise GradingContextError(
                "Période académique incohérente avec l'année du contexte.",
                details={"code": "ACADEMIC_INCONSISTENCY"},
            )
        if period.id_program != ctx.program_id:
            raise GradingContextError(
                "Période académique incohérente avec le programme du contexte.",
                details={
                    "period_program_id": str(period.id_program),
                    "context_program_id": str(ctx.program_id),
                    "code": "ACADEMIC_INCONSISTENCY",
                },
            )


# ---------------------------------------------------------------------------
# Candidate fetch — une requête filtrée (pas de query.first() silencieux)
# ---------------------------------------------------------------------------


def _matching_active_rulesets(db: Session, ctx: ResolutionContext) -> list[GradingRuleset]:
    """Récupère tous les rulesets ACTIVE compatibles (wildcards inclus)."""
    filters = [
        GradingRuleset.school_id == ctx.school_id,
        GradingRuleset.id_annee == ctx.academic_year_id,
        GradingRuleset.status == GRADING_RULESET_STATUS_ACTIVE,
        or_(GradingRuleset.id_program.is_(None), GradingRuleset.id_program == ctx.program_id),
    ]

    if ctx.level_id is not None:
        filters.append(
            or_(GradingRuleset.id_niveau.is_(None), GradingRuleset.id_niveau == ctx.level_id)
        )
    else:
        # Sans niveau dans le contexte : uniquement les wildcards niveau
        filters.append(GradingRuleset.id_niveau.is_(None))

    if ctx.subject_id is not None:
        filters.append(
            or_(GradingRuleset.id_matiere.is_(None), GradingRuleset.id_matiere == ctx.subject_id)
        )
    else:
        filters.append(GradingRuleset.id_matiere.is_(None))

    return (
        db.query(GradingRuleset)
        .options(selectinload(GradingRuleset.components))
        .filter(*filters)
        .all()
    )


def _to_candidate(ruleset: GradingRuleset) -> ResolutionCandidate:
    score = specificity_score_for_ruleset(ruleset)
    return ResolutionCandidate(
        ruleset_id=ruleset.id,
        code=ruleset.code,
        version=ruleset.version,
        status=ruleset.status,
        specificity=score,
        scope_description=scope_description_for(
            id_program=ruleset.id_program,
            id_niveau=ruleset.id_niveau,
            id_matiere=ruleset.id_matiere,
        ),
        id_program=ruleset.id_program,
        id_niveau=ruleset.id_niveau,
        id_matiere=ruleset.id_matiere,
    )


def _build_resolved_components(
    db: Session, ruleset: GradingRuleset
) -> list[ResolvedComponent]:
    components = sorted(ruleset.components, key=lambda c: c.sequence)
    validate_component_weights(components)

    type_ids = {c.id_evaluation_type for c in components}
    types = {
        t.id: t
        for t in db.query(EvaluationType)
        .filter(
            EvaluationType.school_id == ruleset.school_id,
            EvaluationType.id.in_(type_ids),
        )
        .all()
    }
    resolved: list[ResolvedComponent] = []
    for c in components:
        et = types.get(c.id_evaluation_type)
        if et is None:
            raise GradingRulesInvalidError(
                f"Type d'évaluation manquant pour le composant {c.code}.",
                details={"component_id": str(c.id), "evaluation_type_id": str(c.id_evaluation_type)},
            )
        resolved.append(
            ResolvedComponent(
                id=c.id,
                code=c.code,
                label=c.label,
                evaluation_type_id=c.id_evaluation_type,
                evaluation_type_code=et.code,
                evaluation_context=c.evaluation_context,
                weight=Decimal(str(c.weight)),
                sequence=c.sequence,
                is_required=c.is_required,
            )
        )
    return resolved


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_grading_rules(db: Session, ctx: ResolutionContext) -> ResolvedGradingRules:
    """Résout le ruleset ACTIVE applicable au contexte.

    Déterminisme :
    1. Valider le contexte (tenant + cohérence académique)
    2. Charger les candidats ACTIVE matchants
    3. Scorer la spécificité
    4. Si ex-aequo au score max → CONFLICT
    5. Valider les composants du gagnant
    6. Retourner ResolvedGradingRules + trace

    Ne modifie aucune donnée. Ne calcule aucune note.
    """
    validate_resolution_context(db, ctx)

    rulesets = _matching_active_rulesets(db, ctx)
    candidates = [_to_candidate(rs) for rs in rulesets]
    # Tri stable pour la trace uniquement (pas pour le choix)
    candidates_sorted = sorted(
        candidates,
        key=lambda c: (-c.specificity, c.code, c.version, str(c.ruleset_id)),
    )
    trace = ResolutionTrace(candidates=candidates_sorted)

    if not candidates_sorted:
        raise GradingRulesNotFoundError(
            "Aucun ruleset ACTIVE applicable pour ce contexte.",
            details={
                "school_id": str(ctx.school_id),
                "academic_year_id": str(ctx.academic_year_id),
                "program_id": str(ctx.program_id),
                "level_id": str(ctx.level_id) if ctx.level_id else None,
                "class_id": str(ctx.class_id) if ctx.class_id else None,
                "subject_id": str(ctx.subject_id) if ctx.subject_id else None,
                "academic_period_id": str(ctx.academic_period_id) if ctx.academic_period_id else None,
            },
        )

    best_score = candidates_sorted[0].specificity
    winners = [c for c in candidates_sorted if c.specificity == best_score]
    if len(winners) > 1:
        raise GradingRulesConflictError(
            "Plusieurs rulesets ACTIVE de même spécificité — résolution ambiguë.",
            details={
                "school_id": str(ctx.school_id),
                "academic_year_id": str(ctx.academic_year_id),
                "program_id": str(ctx.program_id),
                "level_id": str(ctx.level_id) if ctx.level_id else None,
                "class_id": str(ctx.class_id) if ctx.class_id else None,
                "subject_id": str(ctx.subject_id) if ctx.subject_id else None,
                "academic_period_id": str(ctx.academic_period_id) if ctx.academic_period_id else None,
                "specificity": best_score,
                "conflicting_ruleset_ids": [str(w.ruleset_id) for w in winners],
                "conflicting_codes_versions": [
                    {"id": str(w.ruleset_id), "code": w.code, "version": w.version} for w in winners
                ],
            },
        )

    selected = winners[0]
    trace.selected = selected
    trace.notes.append(
        f"Selected {selected.scope_description} (specificity={selected.specificity}) "
        f"code={selected.code} v{selected.version}"
    )

    ruleset = next(rs for rs in rulesets if rs.id == selected.ruleset_id)
    components = _build_resolved_components(db, ruleset)

    return ResolvedGradingRules(
        ruleset_id=ruleset.id,
        ruleset_code=ruleset.code,
        ruleset_version=ruleset.version,
        school_id=ruleset.school_id,
        specificity=selected.specificity,
        scope_description=selected.scope_description,
        scope_level=scope_level_label(selected.specificity),
        scale_max=Decimal(str(ruleset.scale_max)),
        rounding_mode=ruleset.rounding_mode,
        rounding_precision=ruleset.rounding_precision,
        components=components,
        trace=trace,
    )
