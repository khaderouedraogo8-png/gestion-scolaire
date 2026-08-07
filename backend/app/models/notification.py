from __future__ import annotations

"""Modèle notifications."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_eleve: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    id_parent: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    canal: Mapped[str | None] = mapped_column(String(10))
    type_notification: Mapped[str | None] = mapped_column(String(30))
    contenu: Mapped[str | None] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(String(20), default="en_attente")
    tentative_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    envoye_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
