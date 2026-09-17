from __future__ import annotations

"""Modèles élèves, parents et inscriptions."""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


class ParentTuteur(Base):
    __tablename__ = "parent_tuteur"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    id_utilisateur: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    lien_parente: Mapped[str | None] = mapped_column(String(30))
    telephone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))
    profession: Mapped[str | None] = mapped_column(String(100))
    adresse: Mapped[str | None] = mapped_column(Text)


class Eleve(Base):
    __tablename__ = "eleve"
    __table_args__ = (
        UniqueConstraint("school_id", "matricule", name="uq_eleve_school_matricule"),
        UniqueConstraint("id", "school_id", name="uq_eleve_id_school"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Lien compte utilisateur (rôle eleve) — nullable ; migration deerflow_depth_roles
    id_utilisateur: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    matricule: Mapped[str] = mapped_column(String(30), nullable=False)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    sexe: Mapped[str | None] = mapped_column(String(1))
    date_naissance: Mapped[date | None] = mapped_column(Date)
    lieu_naissance: Mapped[str | None] = mapped_column(String(100))
    adresse: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    notes_medicales_chiffrees: Mapped[bytes | None] = mapped_column()
    pieces_justificatives: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EleveParent(Base):
    """Parent-only : isolation via Eleve / ParentTuteur.school_id."""

    __tablename__ = "eleve_parent"

    id_eleve: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("eleve.id", ondelete="CASCADE"), primary_key=True
    )
    id_parent: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parent_tuteur.id", ondelete="CASCADE"), primary_key=True
    )
    tuteur_legal: Mapped[bool] = mapped_column(Boolean, default=False)


class Inscription(Base):
    __tablename__ = "inscription"
    __table_args__ = (
        ForeignKeyConstraint(
            ["id_eleve", "school_id"],
            ["eleve.id", "eleve.school_id"],
            ondelete="CASCADE",
            name="fk_inscription_eleve_school",
        ),
        ForeignKeyConstraint(
            ["id_classe", "school_id"],
            ["classe.id", "classe.school_id"],
            ondelete="RESTRICT",
            name="fk_inscription_classe_school",
        ),
        ForeignKeyConstraint(
            ["id_annee", "school_id"],
            ["annee_scolaire.id", "annee_scolaire.school_id"],
            ondelete="CASCADE",
            name="fk_inscription_annee_school",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_classe: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_annee: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    statut: Mapped[str] = mapped_column(String(20), default="inscrit", nullable=False)
    est_boursier: Mapped[bool] = mapped_column(Boolean, default=False)
    taux_reduction: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    date_inscription: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    date_statut_maj: Mapped[date | None] = mapped_column(Date)
