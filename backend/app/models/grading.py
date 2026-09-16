from __future__ import annotations

"""Modèles moteur de règles de notation (PR #12 Step 1).

Couche données uniquement — pas de résolution, pas de calcul, pas de template bulletin.
CoefficientMatiere reste inchangé (poids matière ≠ poids d'évaluation).
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
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import Base

# Statuts ruleset
GRADING_RULESET_STATUS_DRAFT = "draft"
GRADING_RULESET_STATUS_ACTIVE = "active"
GRADING_RULESET_STATUS_ARCHIVED = "archived"
GRADING_RULESET_STATUSES = (
    GRADING_RULESET_STATUS_DRAFT,
    GRADING_RULESET_STATUS_ACTIVE,
    GRADING_RULESET_STATUS_ARCHIVED,
)

# Arrondi — aligné sur la future implémentation Decimal
GRADING_ROUNDING_HALF_UP = "half_up"
GRADING_ROUNDING_HALF_EVEN = "half_even"
GRADING_ROUNDING_DOWN = "down"
GRADING_ROUNDING_UP = "up"
GRADING_ROUNDING_MODES = (
    GRADING_ROUNDING_HALF_UP,
    GRADING_ROUNDING_HALF_EVEN,
    GRADING_ROUNDING_DOWN,
    GRADING_ROUNDING_UP,
)

# Contexte d'évaluation ≠ type (préparation architecture ; table dédiée possible plus tard)
EVALUATION_CONTEXT_NORMAL = "normal"
EVALUATION_CONTEXT_EXAMEN_BLANC = "examen_blanc"
EVALUATION_CONTEXT_RATTRAPAGE = "rattrapage"
EVALUATION_CONTEXT_SESSION_2 = "session_2"
EVALUATION_CONTEXTS = (
    EVALUATION_CONTEXT_NORMAL,
    EVALUATION_CONTEXT_EXAMEN_BLANC,
    EVALUATION_CONTEXT_RATTRAPAGE,
    EVALUATION_CONTEXT_SESSION_2,
)

# Catalogue système seedé par école (extensible sans migration SQL)
SYSTEM_EVALUATION_TYPE_CODES: tuple[tuple[str, str], ...] = (
    ("devoir", "Devoir"),
    ("interrogation", "Interrogation"),
    ("composition", "Composition"),
    ("examen", "Examen"),
    ("tp", "Travaux pratiques"),
    ("oral", "Oral"),
    ("projet", "Projet"),
    ("exam_blanc", "Examen blanc"),
    ("rattrapage", "Rattrapage"),
)

# Actions audit (convention log_audit existante — pas de 2e système)
AUDIT_GRADING_RULESET_CREATED = "GRADING_RULESET_CREATED"
AUDIT_GRADING_RULESET_UPDATED = "GRADING_RULESET_UPDATED"
AUDIT_GRADING_RULESET_ACTIVATED = "GRADING_RULESET_ACTIVATED"
AUDIT_GRADING_RULESET_ARCHIVED = "GRADING_RULESET_ARCHIVED"
AUDIT_GRADING_RULE_COMPONENT_CREATED = "GRADING_RULE_COMPONENT_CREATED"
AUDIT_GRADING_RULE_COMPONENT_UPDATED = "GRADING_RULE_COMPONENT_UPDATED"
AUDIT_GRADING_RULE_COMPONENT_DELETED = "GRADING_RULE_COMPONENT_DELETED"

# Convention poids : pourcentages (60.00 + 40.00 = 100.00). Somme validée au service.
WEIGHT_PERCENT_SCALE = Decimal("100.00")
DEFAULT_SCALE_MAX = Decimal("20.00")
DEFAULT_ROUNDING_PRECISION = 2


class EvaluationType(Base):
    """Catalogue de types d'évaluation contrôlés, scopé par école.

    Les types ``is_system`` sont seedés (devoir, composition, …). L'école peut
    ajouter des types custom (``is_system=False``) sans migration SQL.
    ``school_id`` est toujours NOT NULL : isolation tenant stricte + FK composite.
    Le type ≠ le contexte (voir ``GradingRuleComponent.evaluation_context``).
    """

    __tablename__ = "evaluation_type"
    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_evaluation_type_school_code"),
        UniqueConstraint("id", "school_id", name="uq_evaluation_type_id_school"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GradingRuleset(Base):
    """Version cohérente d'un ensemble de règles de notation.

    Versioning : même ``code`` métier + ``version`` entière croissante
    (unique ``school_id, code, version``). Une version publiée reste référencable
    (immuabilité applicative sur active/archived — Step 2+).

    Scope V1 (Gate 1) : School × AcademicYear × Program? × Level? × Subject?
    NULL sur program/level/matiere = wildcard. Pas de Class / Period en V1.
    Aucun HTML/CSS/PDF/template — indépendant du futur BulletinTemplate.
    """

    __tablename__ = "grading_ruleset"
    __table_args__ = (
        UniqueConstraint("school_id", "code", "version", name="uq_grading_ruleset_school_code_version"),
        UniqueConstraint("id", "school_id", name="uq_grading_ruleset_id_school"),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_grading_ruleset_status",
        ),
        CheckConstraint("version >= 1", name="ck_grading_ruleset_version_positive"),
        CheckConstraint("scale_max > 0", name="ck_grading_ruleset_scale_max_positive"),
        CheckConstraint("rounding_precision >= 0", name="ck_grading_ruleset_rounding_precision"),
        CheckConstraint(
            "rounding_mode IN ('half_up', 'half_even', 'down', 'up')",
            name="ck_grading_ruleset_rounding_mode",
        ),
        CheckConstraint(
            "(id_niveau IS NULL) OR (id_program IS NOT NULL)",
            name="ck_grading_ruleset_niveau_requires_program",
        ),
        ForeignKeyConstraint(
            ["id_annee", "school_id"],
            ["annee_scolaire.id", "annee_scolaire.school_id"],
            ondelete="RESTRICT",
            name="fk_grading_ruleset_annee_school",
        ),
        ForeignKeyConstraint(
            ["id_program", "school_id"],
            ["program.id", "program.school_id"],
            ondelete="RESTRICT",
            name="fk_grading_ruleset_program_school",
        ),
        ForeignKeyConstraint(
            ["id_niveau", "school_id"],
            ["niveau_etude.id", "niveau_etude.school_id"],
            ondelete="RESTRICT",
            name="fk_grading_ruleset_niveau_school",
        ),
        ForeignKeyConstraint(
            ["id_matiere", "school_id"],
            ["matiere.id", "matiere.school_id"],
            ondelete="RESTRICT",
            name="fk_grading_ruleset_matiere_school",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=GRADING_RULESET_STATUS_DRAFT, server_default="draft"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    id_annee: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_program: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    id_niveau: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    id_matiere: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    scale_max: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=DEFAULT_SCALE_MAX, server_default="20.00"
    )
    rounding_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default=GRADING_ROUNDING_HALF_UP, server_default="half_up"
    )
    rounding_precision: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=DEFAULT_ROUNDING_PRECISION, server_default="2"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utilisateur.id", ondelete="SET NULL")
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    components: Mapped[list[GradingRuleComponent]] = relationship(
        "GradingRuleComponent",
        back_populates="ruleset",
        cascade="all, delete-orphan",
        order_by="GradingRuleComponent.sequence",
        lazy="selectin",
    )


class GradingRuleComponent(Base):
    """Composante pondérée d'un ruleset (ex. Devoirs 60 %, Composition 40 %).

    ``weight`` = pourcentage (Numeric), convention produit : somme des composants
    d'un ruleset = 100.00 (validation transactionnelle/service — pas un CHECK ligne).
    Distinct de ``CoefficientMatiere.coefficient`` (moyenne générale).
    """

    __tablename__ = "grading_rule_component"
    __table_args__ = (
        UniqueConstraint("ruleset_id", "code", name="uq_grading_rule_component_ruleset_code"),
        UniqueConstraint("ruleset_id", "sequence", name="uq_grading_rule_component_ruleset_sequence"),
        UniqueConstraint("id", "school_id", name="uq_grading_rule_component_id_school"),
        CheckConstraint("weight > 0 AND weight <= 100", name="ck_grading_rule_component_weight"),
        CheckConstraint("sequence >= 1", name="ck_grading_rule_component_sequence"),
        CheckConstraint(
            "evaluation_context IN ('normal', 'examen_blanc', 'rattrapage', 'session_2')",
            name="ck_grading_rule_component_context",
        ),
        ForeignKeyConstraint(
            ["ruleset_id", "school_id"],
            ["grading_ruleset.id", "grading_ruleset.school_id"],
            ondelete="CASCADE",
            name="fk_grading_rule_component_ruleset_school",
        ),
        ForeignKeyConstraint(
            ["id_evaluation_type", "school_id"],
            ["evaluation_type.id", "evaluation_type.school_id"],
            ondelete="RESTRICT",
            name="fk_grading_rule_component_eval_type_school",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ruleset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    id_evaluation_type: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    evaluation_context: Mapped[str] = mapped_column(
        String(40), nullable=False, default=EVALUATION_CONTEXT_NORMAL, server_default="normal"
    )
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    ruleset: Mapped[GradingRuleset] = relationship("GradingRuleset", back_populates="components")
