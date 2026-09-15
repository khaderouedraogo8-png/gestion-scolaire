from __future__ import annotations

"""Résultats académiques persistés (PR #13).

Stocke les sorties du Calculation Engine (et fallback legacy) pour
élève × classe × matière × période, avec traçabilité ruleset.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base

RESULT_SOURCE_RULES_ENGINE = "rules_engine"
RESULT_SOURCE_LEGACY = "legacy"
RESULT_SOURCES = (RESULT_SOURCE_RULES_ENGINE, RESULT_SOURCE_LEGACY)


class AcademicSubjectResult(Base):
    """Moyenne matière persistée pour un élève / période.

    ``is_stale=True`` après modification de notes concernées — recalcul
    au prochain ensure/refresh (bulletin ou endpoint explicite).
    """

    __tablename__ = "academic_subject_result"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "id_eleve",
            "id_classe",
            "id_matiere",
            "id_period",
            name="uq_academic_subject_result_scope",
        ),
        UniqueConstraint("id", "school_id", name="uq_academic_subject_result_id_school"),
        CheckConstraint(
            "source IN ('rules_engine', 'legacy')",
            name="ck_academic_subject_result_source",
        ),
        ForeignKeyConstraint(
            ["id_eleve", "school_id"],
            ["eleve.id", "eleve.school_id"],
            ondelete="CASCADE",
            name="fk_academic_subject_result_eleve_school",
        ),
        ForeignKeyConstraint(
            ["id_classe", "school_id"],
            ["classe.id", "classe.school_id"],
            ondelete="CASCADE",
            name="fk_academic_subject_result_classe_school",
        ),
        ForeignKeyConstraint(
            ["id_matiere", "school_id"],
            ["matiere.id", "matiere.school_id"],
            ondelete="CASCADE",
            name="fk_academic_subject_result_matiere_school",
        ),
        ForeignKeyConstraint(
            ["id_period", "school_id"],
            ["academic_period.id", "academic_period.school_id"],
            ondelete="CASCADE",
            name="fk_academic_subject_result_period_school",
        ),
        ForeignKeyConstraint(
            ["ruleset_id", "school_id"],
            ["grading_ruleset.id", "grading_ruleset.school_id"],
            ondelete="SET NULL",
            name="fk_academic_subject_result_ruleset_school",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    id_classe: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    id_matiere: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    id_period: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    moyenne: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    coefficient: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, default=Decimal(1))
    ruleset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ruleset_version: Mapped[int | None] = mapped_column(Integer)
    ruleset_code: Mapped[str | None] = mapped_column(String(40))
    incomplete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    incomplete_reason: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(20), nullable=False, default=RESULT_SOURCE_RULES_ENGINE)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    calculation_trace: Mapped[list | None] = mapped_column(JSONB)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
