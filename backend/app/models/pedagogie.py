from __future__ import annotations

"""Modèles pédagogie : matières, évaluations, notes, bulletins."""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


class Matiere(Base):
    __tablename__ = "matiere"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    libelle: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str | None] = mapped_column(String(20))


class CoefficientMatiere(Base):
    __tablename__ = "coefficient_matiere"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_matiere: Mapped[uuid.UUID] = mapped_column(ForeignKey("matiere.id", ondelete="CASCADE"), nullable=False)
    id_niveau: Mapped[uuid.UUID] = mapped_column(ForeignKey("niveau_etude.id", ondelete="CASCADE"), nullable=False)
    coefficient: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)


class Evaluation(Base):
    __tablename__ = "evaluation"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_classe: Mapped[uuid.UUID] = mapped_column(ForeignKey("classe.id", ondelete="CASCADE"), nullable=False)
    id_matiere: Mapped[uuid.UUID] = mapped_column(ForeignKey("matiere.id", ondelete="CASCADE"), nullable=False)
    id_trimestre: Mapped[uuid.UUID] = mapped_column(ForeignKey("trimestre.id", ondelete="CASCADE"), nullable=False)
    id_enseignant: Mapped[uuid.UUID] = mapped_column(ForeignKey("enseignant.id", ondelete="RESTRICT"), nullable=False)
    type_evaluation: Mapped[str] = mapped_column(String(20), nullable=False)
    coefficient: Mapped[float] = mapped_column(Numeric(4, 2), default=1, nullable=False)
    date_evaluation: Mapped[date] = mapped_column(Date, nullable=False)
    libelle: Mapped[str | None] = mapped_column(String(150))
    statut_publication: Mapped[str] = mapped_column(String(20), default="brouillon", nullable=False)
    statut_saisie: Mapped[str] = mapped_column(String(20), default="en_cours", nullable=False)


class ProgrammeDevoir(Base):
    __tablename__ = "programme_devoir"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_classe: Mapped[uuid.UUID] = mapped_column(ForeignKey("classe.id", ondelete="CASCADE"), nullable=False)
    id_matiere: Mapped[uuid.UUID] = mapped_column(ForeignKey("matiere.id", ondelete="CASCADE"), nullable=False)
    jour_semaine: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    frequence: Mapped[str] = mapped_column(String(20), default="hebdomadaire", nullable=False)
    note: Mapped[str | None] = mapped_column(String(255))
    id_annee: Mapped[uuid.UUID] = mapped_column(ForeignKey("annee_scolaire.id", ondelete="CASCADE"), nullable=False)


class SeanceCours(Base):
    __tablename__ = "seance_cours"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_classe: Mapped[uuid.UUID] = mapped_column(ForeignKey("classe.id", ondelete="CASCADE"), nullable=False)
    id_matiere: Mapped[uuid.UUID] = mapped_column(ForeignKey("matiere.id", ondelete="CASCADE"), nullable=False)
    id_enseignant: Mapped[uuid.UUID] = mapped_column(ForeignKey("enseignant.id", ondelete="RESTRICT"), nullable=False)
    id_annee: Mapped[uuid.UUID] = mapped_column(ForeignKey("annee_scolaire.id", ondelete="CASCADE"), nullable=False)
    date_seance: Mapped[date] = mapped_column(Date, nullable=False)
    contenu: Mapped[str] = mapped_column(Text, nullable=False)


class Note(Base):
    __tablename__ = "note"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_evaluation: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation.id", ondelete="CASCADE"), nullable=False)
    id_eleve: Mapped[uuid.UUID] = mapped_column(ForeignKey("eleve.id", ondelete="CASCADE"), nullable=False)
    valeur_note: Mapped[float | None] = mapped_column(Numeric(4, 2))
    absent: Mapped[bool] = mapped_column(Boolean, default=False)
    appreciation: Mapped[str | None] = mapped_column(String(255))
    saisi_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateur.id"))
    modifie_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateur.id"))
    saisi_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    modifie_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Bulletin(Base):
    __tablename__ = "bulletin"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_eleve: Mapped[uuid.UUID] = mapped_column(ForeignKey("eleve.id", ondelete="CASCADE"), nullable=False)
    id_trimestre: Mapped[uuid.UUID] = mapped_column(ForeignKey("trimestre.id", ondelete="CASCADE"), nullable=False)
    moyenne_generale: Mapped[float | None] = mapped_column(Numeric(4, 2))
    rang: Mapped[int | None] = mapped_column(Integer)
    effectif_classe: Mapped[int | None] = mapped_column(Integer)
    moyenne_classe: Mapped[float | None] = mapped_column(Numeric(4, 2))
    mention: Mapped[str | None] = mapped_column(String(50))
    appreciation_generale: Mapped[str | None] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(String(20), default="brouillon")
    valide_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateur.id"))
    date_generation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    pdf_url: Mapped[str | None] = mapped_column(Text)
