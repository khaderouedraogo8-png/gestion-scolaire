from __future__ import annotations

"""Modèles finance : frais, échéances, paiements."""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Numeric, Sequence, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base

seq_numero_recu = Sequence("seq_numero_recu")


class FraisScolaire(Base):
    __tablename__ = "frais_scolaire"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_niveau: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_annee: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    motif: Mapped[str] = mapped_column(String(50), nullable=False)
    montant_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)


class EcheancePaiement(Base):
    __tablename__ = "echeance_paiement"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_frais: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    libelle: Mapped[str | None] = mapped_column(String(50))
    montant: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    date_echeance: Mapped[date] = mapped_column(Date, nullable=False)


class Paiement(Base):
    __tablename__ = "paiement"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_annee: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_echeance: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    motif: Mapped[str] = mapped_column(String(50), nullable=False)
    montant_verse: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    mode_paiement: Mapped[str | None] = mapped_column(String(30))
    numero_recu: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    encaisse_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    annule: Mapped[bool] = mapped_column(Boolean, default=False)
    motif_annulation: Mapped[str | None] = mapped_column(Text)
    date_paiement: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
