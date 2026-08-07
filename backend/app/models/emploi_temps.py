from __future__ import annotations

"""Modèles emploi du temps, enseignants, salles."""
import uuid
from datetime import time

from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


class Enseignant(Base):
    __tablename__ = "enseignant"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_utilisateur: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateur.id", ondelete="SET NULL"))
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    specialite: Mapped[str | None] = mapped_column(String(100))
    type_contrat: Mapped[str | None] = mapped_column(String(30))
    taux_horaire: Mapped[float | None] = mapped_column(Numeric(10, 2))
    telephone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))


class AffectationEnseignant(Base):
    __tablename__ = "affectation_enseignant"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_enseignant: Mapped[uuid.UUID] = mapped_column(ForeignKey("enseignant.id", ondelete="CASCADE"), nullable=False)
    id_classe: Mapped[uuid.UUID] = mapped_column(ForeignKey("classe.id", ondelete="CASCADE"), nullable=False)
    id_matiere: Mapped[uuid.UUID] = mapped_column(ForeignKey("matiere.id", ondelete="CASCADE"), nullable=False)
    id_annee: Mapped[uuid.UUID] = mapped_column(ForeignKey("annee_scolaire.id", ondelete="CASCADE"), nullable=False)
    volume_horaire_hebdo: Mapped[float | None] = mapped_column(Numeric(5, 2))


class Salle(Base):
    __tablename__ = "salle"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    libelle: Mapped[str] = mapped_column(String(50), nullable=False)
    capacite: Mapped[int | None] = mapped_column(Integer)


class CreneauEmploiTemps(Base):
    __tablename__ = "creneau_emploi_temps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_affectation: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("affectation_enseignant.id", ondelete="CASCADE"), nullable=False
    )
    id_salle: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("salle.id", ondelete="SET NULL"))
    jour_semaine: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    heure_debut: Mapped[time] = mapped_column(Time, nullable=False)
    heure_fin: Mapped[time] = mapped_column(Time, nullable=False)
