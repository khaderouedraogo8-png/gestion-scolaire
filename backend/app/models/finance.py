from __future__ import annotations

"""Modèles finance : frais, échéances, paiements."""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base

seq_numero_recu = Sequence("seq_numero_recu")


class FraisScolaire(Base):
    __tablename__ = "frais_scolaire"
    __table_args__ = (
        ForeignKeyConstraint(
            ["id_niveau", "school_id"],
            ["niveau_etude.id", "niveau_etude.school_id"],
            ondelete="RESTRICT",
            name="fk_frais_niveau_school",
        ),
        ForeignKeyConstraint(
            ["id_annee", "school_id"],
            ["annee_scolaire.id", "annee_scolaire.school_id"],
            ondelete="CASCADE",
            name="fk_frais_annee_school",
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
    motif: Mapped[str] = mapped_column(String(50), nullable=False)
    montant_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)


class EcheancePaiement(Base):
    """Parent-only : isolation via FraisScolaire.school_id."""

    __tablename__ = "echeance_paiement"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_frais: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    libelle: Mapped[str | None] = mapped_column(String(50))
    montant: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    date_echeance: Mapped[date] = mapped_column(Date, nullable=False)


class Paiement(Base):
    __tablename__ = "paiement"
    __table_args__ = (
        UniqueConstraint("school_id", "numero_recu", name="uq_paiement_school_numero_recu"),
        ForeignKeyConstraint(
            ["id_eleve", "school_id"],
            ["eleve.id", "eleve.school_id"],
            ondelete="CASCADE",
            name="fk_paiement_eleve_school",
        ),
        ForeignKeyConstraint(
            ["id_annee", "school_id"],
            ["annee_scolaire.id", "annee_scolaire.school_id"],
            ondelete="CASCADE",
            name="fk_paiement_annee_school",
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
    id_annee: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_echeance: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    motif: Mapped[str] = mapped_column(String(50), nullable=False)
    montant_verse: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    mode_paiement: Mapped[str | None] = mapped_column(String(30))
    numero_recu: Mapped[str] = mapped_column(String(30), nullable=False)
    encaisse_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    annule: Mapped[bool] = mapped_column(Boolean, default=False)
    motif_annulation: Mapped[str | None] = mapped_column(Text)
    date_paiement: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
