from __future__ import annotations

"""Modèles SQLAlchemy — établissement, année, programme, période académique."""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, synonym

from app.extensions import Base

# Program.GENERAL — compatibilité historique (ne pas supprimer automatiquement)
PROGRAM_CODE_GENERAL = "GENERAL"
PROGRAM_NAME_GENERAL = "Général"


class Etablissement(Base):
    __tablename__ = "etablissement"
    __table_args__ = (UniqueConstraint("school_id", name="uq_etablissement_school_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nom: Mapped[str] = mapped_column(String(150), nullable=False)
    sigle: Mapped[str | None] = mapped_column(String(20))
    adresse: Mapped[str | None] = mapped_column(Text)
    telephone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))
    logo_url: Mapped[str | None] = mapped_column(Text)
    type_etablissement: Mapped[str | None] = mapped_column(String(50))
    pays: Mapped[str | None] = mapped_column(String(80))
    ville: Mapped[str | None] = mapped_column(String(80))
    format_matricule: Mapped[str] = mapped_column(String(50), default="{ANNEE}M-{SEQ}")
    matricule_sequence: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0"
    )
    devise: Mapped[str] = mapped_column(String(10), default="XOF")
    bulletin_template: Mapped[str] = mapped_column(String(20), default="BF")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AnneeScolaire(Base):
    __tablename__ = "annee_scolaire"
    __table_args__ = (
        UniqueConstraint("school_id", "libelle", name="uq_annee_scolaire_school_libelle"),
        UniqueConstraint("id", "school_id", name="uq_annee_scolaire_id_school"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    libelle: Mapped[str] = mapped_column(String(20), nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    est_active: Mapped[bool] = mapped_column(Boolean, default=False)


class Program(Base):
    """Filière / programme scolaire — school-scoped.

    Extensible vers Track/Parcours dans une PR future sans migration destructive.
    ``period_type_default`` est un défaut UX uniquement (jamais pour le calcul des notes).
    Le code ``GENERAL`` est le programme de compatibilité historique permanent.
    """

    __tablename__ = "program"
    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_program_school_code"),
        UniqueConstraint("id", "school_id", name="uq_program_id_school"),
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
    # VARCHAR extensible (pas d'enum SQL figée) — valeurs usuelles :
    # general | technique | professionnel | custom
    program_type: Mapped[str] = mapped_column(String(40), nullable=False, default="general")
    period_type_default: Mapped[str] = mapped_column(String(20), nullable=False, default="trimestre")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AcademicPeriod(Base):
    """Période académique (évolution de Trimestre) — Model B : Year + Program.

    Les UUID historiques de ``trimestre`` sont conservés.
    ``numero`` est un synonyme legacy de ``sequence`` pour la façade API /trimestres.
    """

    __tablename__ = "academic_period"
    __table_args__ = (
        UniqueConstraint("id", "school_id", name="uq_academic_period_id_school"),
        UniqueConstraint("id_annee", "id_program", "sequence", name="uq_academic_period_year_program_sequence"),
        UniqueConstraint("id_annee", "id_program", "code", name="uq_academic_period_year_program_code"),
        CheckConstraint("sequence >= 1", name="ck_academic_period_sequence_positive"),
        CheckConstraint("date_fin >= date_debut", name="ck_academic_period_dates"),
        CheckConstraint(
            "period_type IN ('trimestre', 'semestre', 'custom', 'annuel')",
            name="ck_academic_period_type",
        ),
        ForeignKeyConstraint(
            ["id_annee", "school_id"],
            ["annee_scolaire.id", "annee_scolaire.school_id"],
            ondelete="CASCADE",
            name="fk_academic_period_annee_school",
        ),
        ForeignKeyConstraint(
            ["id_program", "school_id"],
            ["program.id", "program.school_id"],
            ondelete="RESTRICT",
            name="fk_academic_period_program_school",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    id_annee: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_program: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False, default="trimestre")
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Compat façade /trimestres et code legacy
    numero = synonym("sequence")


# Alias legacy — une seule source de vérité métier (AcademicPeriod)
Trimestre = AcademicPeriod


class NiveauEtude(Base):
    __tablename__ = "niveau_etude"
    __table_args__ = (
        UniqueConstraint("school_id", "id_program", "libelle", name="uq_niveau_etude_school_program_libelle"),
        UniqueConstraint("id", "school_id", name="uq_niveau_etude_id_school"),
        UniqueConstraint("id", "id_program", name="uq_niveau_etude_id_program"),
        ForeignKeyConstraint(
            ["id_program", "school_id"],
            ["program.id", "program.school_id"],
            ondelete="RESTRICT",
            name="fk_niveau_etude_program_school",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    id_program: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    libelle: Mapped[str] = mapped_column(String(50), nullable=False)
    ordre: Mapped[int | None] = mapped_column(SmallInteger)
    cycle: Mapped[str] = mapped_column(String(20), nullable=False, default="premier")


class Classe(Base):
    __tablename__ = "classe"
    __table_args__ = (
        UniqueConstraint("id", "school_id", name="uq_classe_id_school"),
        ForeignKeyConstraint(
            ["id_niveau", "school_id"],
            ["niveau_etude.id", "niveau_etude.school_id"],
            ondelete="RESTRICT",
            name="fk_classe_niveau_school",
        ),
        ForeignKeyConstraint(
            ["id_annee", "school_id"],
            ["annee_scolaire.id", "annee_scolaire.school_id"],
            ondelete="CASCADE",
            name="fk_classe_annee_school",
        ),
        ForeignKeyConstraint(
            ["id_program", "school_id"],
            ["program.id", "program.school_id"],
            ondelete="RESTRICT",
            name="fk_classe_program_school",
        ),
        ForeignKeyConstraint(
            ["id_niveau", "id_program"],
            ["niveau_etude.id", "niveau_etude.id_program"],
            ondelete="RESTRICT",
            name="fk_classe_niveau_program",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    id_niveau: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_annee: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_program: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    libelle: Mapped[str] = mapped_column(String(50), nullable=False)
    id_professeur_principal: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    capacite_max: Mapped[int] = mapped_column(default=50)


class EvenementCalendrier(Base):
    """Parent-only : isolation via AnneeScolaire.school_id."""

    __tablename__ = "evenement_calendrier"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_annee: Mapped[uuid.UUID] = mapped_column(ForeignKey("annee_scolaire.id", ondelete="CASCADE"), nullable=False)
    type_evenement: Mapped[str] = mapped_column(String(30), nullable=False)
    libelle: Mapped[str] = mapped_column(String(150), nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    bloque_programmation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
