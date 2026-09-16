"""Helpers catalogue evaluation_type (PR #12 Step 1 / PR #15)."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.grading import SYSTEM_EVALUATION_TYPE_CODES, EvaluationType
from app.services.tenant import tenant_query
from app.utils.errors import abort_api


def ensure_system_evaluation_types(db: Session, school_id: uuid.UUID) -> list[EvaluationType]:
    """Seed idempotent des types système pour une école (tenant-safe)."""
    existing = {
        row.code: row
        for row in db.query(EvaluationType)
        .filter(EvaluationType.school_id == school_id, EvaluationType.is_system.is_(True))
        .all()
    }
    created: list[EvaluationType] = []
    for code, label in SYSTEM_EVALUATION_TYPE_CODES:
        if code in existing:
            continue
        row = EvaluationType(
            id=uuid.uuid4(),
            school_id=school_id,
            code=code,
            label=label,
            is_system=True,
            is_active=True,
        )
        db.add(row)
        created.append(row)
        existing[code] = row
    if created:
        db.flush()
    return list(existing.values())


def get_active_evaluation_type_by_code(db: Session, code: str) -> EvaluationType:
    """Résout un type d'évaluation actif du tenant courant (PR15-A).

    Source de vérité = table ``evaluation_type`` (pas une liste hardcodée).
    """
    normalized = (code or "").strip().lower()
    if not normalized:
        abort_api(400, "INVALID_EVALUATION_TYPE", "type_evaluation est obligatoire.")
    if len(normalized) > 20:
        abort_api(
            400,
            "INVALID_EVALUATION_TYPE",
            "type_evaluation trop long (max 20 caractères).",
            details={"code": normalized},
        )
    et = (
        tenant_query(EvaluationType)
        .filter(EvaluationType.code == normalized)
        .first()
    )
    if et is None:
        abort_api(
            400,
            "INVALID_EVALUATION_TYPE",
            f"Type d'évaluation « {normalized} » inconnu pour cette école.",
            details={"code": normalized},
        )
    if not et.is_active:
        abort_api(
            400,
            "INVALID_EVALUATION_TYPE",
            f"Type d'évaluation « {et.code} » inactif.",
            details={"evaluation_type_id": str(et.id), "code": et.code},
        )
    return et
