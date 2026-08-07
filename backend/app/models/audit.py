from __future__ import annotations

"""Modèle journal d'audit."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


class JournalAudit(Base):
    __tablename__ = "journal_audit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_utilisateur: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    table_cible: Mapped[str | None] = mapped_column(String(50))
    id_enregistrement_cible: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ip_origine: Mapped[str | None] = mapped_column(INET)
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
