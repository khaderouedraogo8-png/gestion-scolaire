"""PR #12 Step 4 — orchestration calcul académique (DB + résolution + moteur).

Flux :
  Contexte académique → resolve_grading_rules (Step 2) → calculate_subject_result
Jamais d'appel HTTP vers l'API Step 3.
Cache in-memory par clé de contexte (même classe/matière/période).
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.etablissement import AcademicPeriod, Classe
from app.models.pedagogie import CoefficientMatiere, Evaluation, Matiere, Note
from app.services.academic_calculation import (
    GeneralAverageResult,
    GradeInput,
    SubjectResult,
    calculate_general_average,
    calculate_subject_result,
)
from app.services.grading_rules import (
    GradingContextError,
    GradingRulesConflictError,
    GradingRulesInvalidError,
    GradingRulesNotFoundError,
    ResolutionContext,
    ResolvedGradingRules,
    resolve_grading_rules,
)
from app.services.tenant import get_current_school_id, get_or_404_tenant


class RulesResolutionCache:
    """Cache de rulesets résolus pour un calcul de classe (pas Redis)."""

    def __init__(self) -> None:
        self._hits: dict[tuple, ResolvedGradingRules | None] = {}
        self._errors: dict[tuple, Exception] = {}

    @staticmethod
    def _key(ctx: ResolutionContext) -> tuple:
        return (
            ctx.school_id,
            ctx.academic_year_id,
            ctx.program_id,
            ctx.level_id,
            ctx.class_id,
            ctx.subject_id,
            ctx.academic_period_id,
        )

    def get_or_resolve(self, db: Session, ctx: ResolutionContext) -> ResolvedGradingRules:
        key = self._key(ctx)
        if key in self._errors:
            raise self._errors[key]
        if key in self._hits:
            rules = self._hits[key]
            if rules is None:
                raise GradingRulesNotFoundError("Aucun ruleset ACTIVE (cache).")
            return rules
        try:
            rules = resolve_grading_rules(db, ctx)
        except (
            GradingRulesNotFoundError,
            GradingRulesConflictError,
            GradingContextError,
            GradingRulesInvalidError,
        ) as exc:
            self._errors[key] = exc
            raise
        self._hits[key] = rules
        return rules


def _subject_coefficient(
    db: Session, *, id_matiere: uuid.UUID, id_niveau: uuid.UUID | None
) -> Decimal:
    if id_niveau is None:
        return Decimal(1)
    row = (
        db.query(CoefficientMatiere)
        .filter(
            CoefficientMatiere.id_matiere == id_matiere,
            CoefficientMatiere.id_niveau == id_niveau,
        )
        .first()
    )
    if row is None:
        return Decimal(1)
    return Decimal(str(row.coefficient))


def load_grades_for_student_subject_period(
    db: Session,
    *,
    id_eleve: uuid.UUID,
    id_classe: uuid.UUID,
    id_matiere: uuid.UUID,
    id_period: uuid.UUID,
) -> list[GradeInput]:
    """Charge les notes d'un élève pour une matière/période (tenant-safe)."""
    school_id = get_current_school_id()
    rows = (
        db.query(Note, Evaluation)
        .join(Evaluation, Evaluation.id == Note.id_evaluation)
        .filter(
            Note.id_eleve == id_eleve,
            Note.school_id == school_id,
            Evaluation.school_id == school_id,
            Evaluation.id_classe == id_classe,
            Evaluation.id_matiere == id_matiere,
            Evaluation.id_trimestre == id_period,
        )
        .all()
    )
    grades: list[GradeInput] = []
    for note, evaluation in rows:
        valeur = None if note.valeur_note is None else Decimal(str(note.valeur_note))
        grades.append(
            GradeInput(
                evaluation_id=evaluation.id,
                evaluation_type_code=(evaluation.type_evaluation or "").strip().lower(),
                valeur=valeur,
                absent=bool(note.absent),
            )
        )
    return grades


def load_all_grades_for_class_period(
    db: Session,
    *,
    id_classe: uuid.UUID,
    id_period: uuid.UUID,
) -> dict[tuple[uuid.UUID, uuid.UUID], list[GradeInput]]:
    """Batch : {(id_eleve, id_matiere): [GradeInput]} pour une classe/période."""
    school_id = get_current_school_id()
    rows = (
        db.query(Note, Evaluation)
        .join(Evaluation, Evaluation.id == Note.id_evaluation)
        .filter(
            Note.school_id == school_id,
            Evaluation.school_id == school_id,
            Evaluation.id_classe == id_classe,
            Evaluation.id_trimestre == id_period,
        )
        .all()
    )
    out: dict[tuple[uuid.UUID, uuid.UUID], list[GradeInput]] = {}
    for note, evaluation in rows:
        key = (note.id_eleve, evaluation.id_matiere)
        valeur = None if note.valeur_note is None else Decimal(str(note.valeur_note))
        out.setdefault(key, []).append(
            GradeInput(
                evaluation_id=evaluation.id,
                evaluation_type_code=(evaluation.type_evaluation or "").strip().lower(),
                valeur=valeur,
                absent=bool(note.absent),
            )
        )
    return out


def build_resolution_context_for_classe(
    db: Session,
    *,
    classe: Classe,
    period: AcademicPeriod,
    subject_id: uuid.UUID,
) -> ResolutionContext:
    """Contexte complet pour résoudre un ruleset (tenant via get_current_school_id)."""
    school_id = get_current_school_id()
    if classe.school_id != school_id or period.school_id != school_id:
        raise GradingContextError(
            "Classe ou période hors tenant.",
            details={"code": "TENANT_CONTEXT_ERROR"},
        )
    if period.id_annee != classe.id_annee:
        raise GradingContextError(
            "Période incohérente avec l'année de la classe.",
            details={"code": "ACADEMIC_INCONSISTENCY"},
        )
    if period.id_program != classe.id_program:
        raise GradingContextError(
            "Période incohérente avec le programme de la classe.",
            details={"code": "ACADEMIC_INCONSISTENCY"},
        )
    get_or_404_tenant(Matiere, subject_id)
    return ResolutionContext(
        school_id=school_id,
        academic_year_id=classe.id_annee,
        program_id=classe.id_program,
        level_id=classe.id_niveau,
        class_id=classe.id,
        subject_id=subject_id,
        academic_period_id=period.id,
    )


def calculate_student_subject(
    db: Session,
    *,
    id_eleve: uuid.UUID,
    classe: Classe,
    period: AcademicPeriod,
    subject_id: uuid.UUID,
    cache: RulesResolutionCache | None = None,
    grades: list[GradeInput] | None = None,
) -> SubjectResult:
    """Résout le ruleset puis calcule la moyenne matière pour un élève."""
    cache = cache or RulesResolutionCache()
    ctx = build_resolution_context_for_classe(
        db, classe=classe, period=period, subject_id=subject_id
    )
    rules = cache.get_or_resolve(db, ctx)
    if grades is None:
        grades = load_grades_for_student_subject_period(
            db,
            id_eleve=id_eleve,
            id_classe=classe.id,
            id_matiere=subject_id,
            id_period=period.id,
        )
    coef = _subject_coefficient(db, id_matiere=subject_id, id_niveau=classe.id_niveau)
    return calculate_subject_result(
        grades, rules, subject_id=subject_id, subject_coefficient=coef
    )


def calculate_student_period_results(
    db: Session,
    *,
    id_eleve: uuid.UUID,
    id_classe: uuid.UUID,
    id_period: uuid.UUID,
    cache: RulesResolutionCache | None = None,
    subject_ids: list[uuid.UUID] | None = None,
) -> tuple[list[SubjectResult], GeneralAverageResult | None, dict[str, Any]]:
    """Calcule toutes les matières d'un élève pour une période via le Rules Engine.

    Retourne (subject_results, general_average, meta).
    Si aucun ruleset pour une matière → cette matière est absente de subject_results
    et listée dans meta['legacy_fallback_subjects'] (le caller peut utiliser la vue).
    """
    cache = cache or RulesResolutionCache()
    classe = get_or_404_tenant(Classe, id_classe)
    period = get_or_404_tenant(AcademicPeriod, id_period)
    grades_map = load_all_grades_for_class_period(
        db, id_classe=id_classe, id_period=id_period
    )

    if subject_ids is None:
        subject_ids = sorted(
            {mid for (eid, mid) in grades_map if eid == id_eleve},
            key=str,
        )
        # Inclure aussi les matières avec coefficient même sans notes ? Non — pas de 0 auto.

    results: list[SubjectResult] = []
    legacy_subjects: list[str] = []
    conflicts: list[str] = []
    meta: dict[str, Any] = {
        "legacy_fallback_subjects": legacy_subjects,
        "conflicts": conflicts,
        "ruleset_versions": {},
    }

    for subject_id in subject_ids:
        try:
            sr = calculate_student_subject(
                db,
                id_eleve=id_eleve,
                classe=classe,
                period=period,
                subject_id=subject_id,
                cache=cache,
                grades=grades_map.get((id_eleve, subject_id), []),
            )
            results.append(sr)
            meta["ruleset_versions"][str(subject_id)] = {
                "ruleset_id": str(sr.ruleset_id),
                "version": sr.ruleset_version,
                "code": sr.ruleset_code,
            }
        except GradingRulesNotFoundError:
            legacy_subjects.append(str(subject_id))
        except GradingRulesConflictError as exc:
            conflicts.append(str(exc.message))
            raise
        except GradingContextError:
            raise

    ga = calculate_general_average(results) if results else None
    return results, ga, meta


def subject_results_to_moyenne_rows(
    db: Session, results: list[SubjectResult]
) -> list[dict]:
    """Adaptateur bulletin : format compatible ``_get_moyennes_eleve``."""
    rows = []
    for sr in results:
        matiere = get_or_404_tenant(Matiere, sr.subject_id) if sr.subject_id else None
        rows.append(
            {
                "id_matiere": sr.subject_id,
                "libelle": matiere.libelle if matiere else None,
                "moyenne": sr.as_float_average(),
                "coefficient": float(sr.coefficient),
                "ruleset_id": str(sr.ruleset_id),
                "ruleset_version": sr.ruleset_version,
                "ruleset_code": sr.ruleset_code,
                "incomplete": sr.incomplete,
                "calculation_trace": list(sr.calculation_trace),
            }
        )
    return rows
