from __future__ import annotations

"""Modèles SQLAlchemy — établissement, année, trimestre."""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


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
    devise: Mapped[str] = mapped_column(String(10), default="XOF")
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


class Trimestre(Base):
    """Parent-only : isolation via AnneeScolaire.school_id."""

    __tablename__ = "trimestre"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_annee: Mapped[uuid.UUID] = mapped_column(ForeignKey("annee_scolaire.id", ondelete="CASCADE"), nullable=False)
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)


class NiveauEtude(Base):
    __tablename__ = "niveau_etude"
    __table_args__ = (
        UniqueConstraint("school_id", "libelle", name="uq_niveau_etude_school_libelle"),
        UniqueConstraint("id", "school_id", name="uq_niveau_etude_id_school"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
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
