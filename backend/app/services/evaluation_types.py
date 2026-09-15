"""Helpers catalogue evaluation_type (PR #12 Step 1)."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.grading import SYSTEM_EVALUATION_TYPE_CODES, EvaluationType


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
