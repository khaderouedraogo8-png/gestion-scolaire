"""PR #13/#15 — persistance et invalidation des résultats académiques.

Calcule via academic_calculation_service, upsert dans academic_subject_result.
PR15-B : plus de fallback silencieux vers la vue MV legacy — matière sans
ruleset / conflit → incomplete (moyenne None), source rules_engine.
Le bulletin (PR15-C) consomme uniquement ce store.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from flask import current_app
from sqlalchemy.orm import Session

from app.models.academic_results import (
    RESULT_SOURCE_RULES_ENGINE,
    AcademicSubjectResult,
)
from app.models.etablissement import AcademicPeriod, Classe
from app.models.pedagogie import CoefficientMatiere, Evaluation, Matiere
from app.services.academic_calculation_service import (
    RulesResolutionCache,
    calculate_student_period_results,
    load_all_grades_for_class_period,
)
from app.services.grading_rules import GradingContextError, GradingRulesConflictError
from app.services.tenant import apply_tenant_school, get_current_school_id, get_or_404_tenant, tenant_query

INCOMPLETE_NO_RULESET = "NO_RULESET"


def _now() -> datetime:
    return datetime.now(UTC)


def _subject_coefficient(db: Session, *, id_matiere: uuid.UUID, id_niveau: uuid.UUID | None) -> Decimal:
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


def _upsert_result(
    db: Session,
    *,
    existing: AcademicSubjectResult | None,
    id_eleve: uuid.UUID,
    id_classe: uuid.UUID,
    id_matiere: uuid.UUID,
    id_period: uuid.UUID,
    moyenne: Decimal | float | None,
    coefficient: Decimal | float,
    scale_max: Decimal | float | None,
    ruleset_id: uuid.UUID | None,
    ruleset_version: int | None,
    ruleset_code: str | None,
    incomplete: bool,
    incomplete_reason: str | None,
    source: str,
    calculation_trace: list[str] | None,
) -> AcademicSubjectResult:
    moy = None if moyenne is None else Decimal(str(moyenne))
    coef = Decimal(str(coefficient))
    scale = None if scale_max is None else Decimal(str(scale_max))
    now = _now()
    if existing is None:
        row = AcademicSubjectResult(
            id=uuid.uuid4(),
            id_eleve=id_eleve,
            id_classe=id_classe,
            id_matiere=id_matiere,
            id_period=id_period,
            moyenne=moy,
            coefficient=coef,
            scale_max=scale,
            ruleset_id=ruleset_id,
            ruleset_version=ruleset_version,
            ruleset_code=ruleset_code,
            incomplete=incomplete,
            incomplete_reason=incomplete_reason,
            source=source,
            is_stale=False,
            calculation_trace=calculation_trace,
            calculated_at=now,
        )
        apply_tenant_school(row)
        db.add(row)
        return row

    existing.moyenne = moy
    existing.coefficient = coef
    existing.scale_max = scale
    existing.ruleset_id = ruleset_id
    existing.ruleset_version = ruleset_version
    existing.ruleset_code = ruleset_code
    existing.incomplete = incomplete
    existing.incomplete_reason = incomplete_reason
    existing.source = source
    existing.is_stale = False
    existing.calculation_trace = calculation_trace
    existing.calculated_at = now
    return existing


def list_results_for_student_period(
    db: Session,
    *,
    id_eleve: uuid.UUID,
    id_classe: uuid.UUID,
    id_period: uuid.UUID,
) -> list[AcademicSubjectResult]:
    return (
        tenant_query(AcademicSubjectResult)
        .filter(
            AcademicSubjectResult.id_eleve == id_eleve,
            AcademicSubjectResult.id_classe == id_classe,
            AcademicSubjectResult.id_period == id_period,
        )
        .order_by(AcademicSubjectResult.id_matiere)
        .all()
    )


def results_need_refresh(rows: list[AcademicSubjectResult]) -> bool:
    if not rows:
        return True
    return any(r.is_stale for r in rows)


def mark_stale_for_evaluation(db: Session, evaluation: Evaluation) -> int:
    """Marque stale les résultats matière/période/classe de l'évaluation."""
    school_id = get_current_school_id()
    q = (
        db.query(AcademicSubjectResult)
        .filter(
            AcademicSubjectResult.school_id == school_id,
            AcademicSubjectResult.id_classe == evaluation.id_classe,
            AcademicSubjectResult.id_matiere == evaluation.id_matiere,
            AcademicSubjectResult.id_period == evaluation.id_trimestre,
            AcademicSubjectResult.is_stale.is_(False),
        )
    )
    count = 0
    for row in q.all():
        row.is_stale = True
        count += 1
    return count


def persist_student_period_results(
    db: Session,
    *,
    id_eleve: uuid.UUID,
    id_classe: uuid.UUID,
    id_period: uuid.UUID,
    cache: RulesResolutionCache | None = None,
) -> list[AcademicSubjectResult]:
    """Calcule et upsert tous les résultats matière d'un élève pour une période.

    PR15-B : Calculation Engine uniquement. Sans ruleset / conflit → incomplete
    (moyenne None). Jamais de moyenne MV legacy silencieuse.
    """
    cache = cache or RulesResolutionCache()
    classe = get_or_404_tenant(Classe, id_classe)
    get_or_404_tenant(AcademicPeriod, id_period)

    existing_rows = list_results_for_student_period(
        db, id_eleve=id_eleve, id_classe=id_classe, id_period=id_period
    )
    existing_by_matiere = {r.id_matiere: r for r in existing_rows}

    engine_by_matiere: dict[uuid.UUID, Any] = {}
    meta: dict[str, Any] = {
        "legacy_fallback_subjects": [],
        "conflicts": [],
        "ruleset_versions": {},
    }
    period_block_reason: str | None = None
    subject_ids: set[uuid.UUID] = set()

    try:
        # subject_ids=None → découverte via notes (grades_map), pas via MV
        results, _ga, meta = calculate_student_period_results(
            db,
            id_eleve=id_eleve,
            id_classe=id_classe,
            id_period=id_period,
            cache=cache,
            subject_ids=None,
        )
        engine_by_matiere = {sr.subject_id: sr for sr in results if sr.subject_id}
    except (GradingRulesConflictError, GradingContextError) as exc:
        current_app.logger.warning(
            "academic_results_incomplete eleve=%s classe=%s periode=%s err=%s",
            id_eleve,
            id_classe,
            id_period,
            exc,
        )
        period_block_reason = getattr(exc, "message", None) or str(exc)
        grades_map = load_all_grades_for_class_period(
            db, id_classe=id_classe, id_period=id_period
        )
        subject_ids.update(mid for (eid, mid) in grades_map if eid == id_eleve)

    subject_ids.update(engine_by_matiere.keys())
    subject_ids.update(existing_by_matiere.keys())
    for mid in meta.get("legacy_fallback_subjects") or []:
        subject_ids.add(uuid.UUID(str(mid)))

    persisted: list[AcademicSubjectResult] = []
    seen: set[uuid.UUID] = set()

    for mid in sorted(subject_ids, key=str):
        seen.add(mid)
        existing = existing_by_matiere.get(mid)
        coef = _subject_coefficient(db, id_matiere=mid, id_niveau=classe.id_niveau)

        if period_block_reason:
            persisted.append(
                _upsert_result(
                    db,
                    existing=existing,
                    id_eleve=id_eleve,
                    id_classe=id_classe,
                    id_matiere=mid,
                    id_period=id_period,
                    moyenne=None,
                    coefficient=coef,
                    scale_max=None,
                    ruleset_id=None,
                    ruleset_version=None,
                    ruleset_code=None,
                    incomplete=True,
                    incomplete_reason=period_block_reason[:255],
                    source=RESULT_SOURCE_RULES_ENGINE,
                    calculation_trace=None,
                )
            )
            continue

        if mid in engine_by_matiere:
            sr = engine_by_matiere[mid]
            persisted.append(
                _upsert_result(
                    db,
                    existing=existing,
                    id_eleve=id_eleve,
                    id_classe=id_classe,
                    id_matiere=mid,
                    id_period=id_period,
                    moyenne=sr.subject_average,
                    coefficient=sr.coefficient,
                    scale_max=sr.scale_max,
                    ruleset_id=sr.ruleset_id,
                    ruleset_version=sr.ruleset_version,
                    ruleset_code=sr.ruleset_code,
                    incomplete=bool(sr.incomplete),
                    incomplete_reason=sr.incomplete_reason,
                    source=RESULT_SOURCE_RULES_ENGINE,
                    calculation_trace=list(sr.calculation_trace) if sr.calculation_trace else None,
                )
            )
            continue

        # Pas de ruleset ACTIVE pour cette matière (ex-legacy_fallback)
        persisted.append(
            _upsert_result(
                db,
                existing=existing,
                id_eleve=id_eleve,
                id_classe=id_classe,
                id_matiere=mid,
                id_period=id_period,
                moyenne=None,
                coefficient=coef,
                scale_max=None,
                ruleset_id=None,
                ruleset_version=None,
                ruleset_code=None,
                incomplete=True,
                incomplete_reason=INCOMPLETE_NO_RULESET,
                source=RESULT_SOURCE_RULES_ENGINE,
                calculation_trace=None,
            )
        )

    for mid, row in existing_by_matiere.items():
        if mid not in seen:
            db.delete(row)

    db.flush()
    return list_results_for_student_period(
        db, id_eleve=id_eleve, id_classe=id_classe, id_period=id_period
    )


def ensure_student_period_results(
    db: Session,
    *,
    id_eleve: uuid.UUID,
    id_classe: uuid.UUID,
    id_period: uuid.UUID,
    cache: RulesResolutionCache | None = None,
    force: bool = False,
) -> list[AcademicSubjectResult]:
    """Retourne les résultats frais (recalc si absents/stale ou force)."""
    rows = list_results_for_student_period(
        db, id_eleve=id_eleve, id_classe=id_classe, id_period=id_period
    )
    if force or results_need_refresh(rows):
        return persist_student_period_results(
            db,
            id_eleve=id_eleve,
            id_classe=id_classe,
            id_period=id_period,
            cache=cache,
        )
    return rows


def results_to_moyenne_rows(db: Session, rows: list[AcademicSubjectResult]) -> list[dict]:
    """Format compatible bulletin / moyenne générale."""
    out = []
    for r in rows:
        matiere = get_or_404_tenant(Matiere, r.id_matiere)
        out.append(
            {
                "id_matiere": r.id_matiere,
                "libelle": matiere.libelle,
                "moyenne": float(r.moyenne) if r.moyenne is not None else None,
                "coefficient": float(r.coefficient) if r.coefficient is not None else 1.0,
                "scale_max": float(r.scale_max) if r.scale_max is not None else None,
                "ruleset_id": str(r.ruleset_id) if r.ruleset_id else None,
                "ruleset_version": r.ruleset_version,
                "ruleset_code": r.ruleset_code,
                "incomplete": bool(r.incomplete),
                "incomplete_reason": r.incomplete_reason,
                "source": r.source,
                "is_stale": bool(r.is_stale),
                "calculated_at": r.calculated_at.isoformat() if r.calculated_at else None,
            }
        )
    return out


def build_rulesets_snapshot(rows: list[AcademicSubjectResult]) -> list[dict]:
    """Déduplique les rulesets utilisés pour stocker sur bulletin."""
    seen: dict[str, dict] = {}
    for r in rows:
        if not r.ruleset_id:
            continue
        key = str(r.ruleset_id)
        if key not in seen:
            seen[key] = {
                "ruleset_id": key,
                "version": r.ruleset_version,
                "code": r.ruleset_code,
                "subject_ids": [],
            }
        seen[key]["subject_ids"].append(str(r.id_matiere))
    return list(seen.values())


def serialize_result_row(db: Session, row: AcademicSubjectResult) -> dict:
    matiere = tenant_query(Matiere).filter(Matiere.id == row.id_matiere).first()
    return {
        "id": str(row.id),
        "id_eleve": str(row.id_eleve),
        "id_classe": str(row.id_classe),
        "id_matiere": str(row.id_matiere),
        "matiere_libelle": matiere.libelle if matiere else None,
        "id_period": str(row.id_period),
        "moyenne": float(row.moyenne) if row.moyenne is not None else None,
        "coefficient": float(row.coefficient) if row.coefficient is not None else 1.0,
        "scale_max": float(row.scale_max) if row.scale_max is not None else None,
        "ruleset_id": str(row.ruleset_id) if row.ruleset_id else None,
        "ruleset_version": row.ruleset_version,
        "ruleset_code": row.ruleset_code,
        "incomplete": bool(row.incomplete),
        "incomplete_reason": row.incomplete_reason,
        "source": row.source,
        "is_stale": bool(row.is_stale),
        "calculated_at": row.calculated_at.isoformat() if row.calculated_at else None,
    }
