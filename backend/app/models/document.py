from __future__ import annotations

"""Modèle documents administratifs."""
import uuid
from datetime import date

from sqlalchemy import Date, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


class DocumentAdministratif(Base):
    __tablename__ = "document_administratif"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    type_document: Mapped[str | None] = mapped_column(String(30))
    qr_code_data: Mapped[str | None] = mapped_column(Text)
    date_emission: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    date_expiration: Mapped[date | None] = mapped_column(Date)
    pdf_url: Mapped[str | None] = mapped_column(Text)
    genere_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
