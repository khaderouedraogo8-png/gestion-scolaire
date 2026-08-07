from __future__ import annotations

"""Modèles absences et discipline."""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


class Absence(Base):
    __tablename__ = "absence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_creneau: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    date_absence: Mapped[date] = mapped_column(Date, nullable=False)
    type_absence: Mapped[str | None] = mapped_column(String(20))
    justifiee: Mapped[bool] = mapped_column(Boolean, default=False)
    motif: Mapped[str | None] = mapped_column(Text)
    signale_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IncidentDisciplinaire(Base):
    __tablename__ = "incident_disciplinaire"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_trimestre: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    type_incident: Mapped[str | None] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    date_incident: Mapped[date] = mapped_column(Date, nullable=False)
    declare_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
