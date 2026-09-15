from __future__ import annotations

"""Modèles emploi du temps, enseignants, salles."""
import uuid
from datetime import time

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Integer, Numeric, SmallInteger, String, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


class Enseignant(Base):
    __tablename__ = "enseignant"
    __table_args__ = (UniqueConstraint("id", "school_id", name="uq_enseignant_id_school"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
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
    __table_args__ = (
        ForeignKeyConstraint(
            ["id_enseignant", "school_id"],
            ["enseignant.id", "enseignant.school_id"],
            ondelete="CASCADE",
            name="fk_affectation_enseignant_school",
        ),
        ForeignKeyConstraint(
            ["id_classe", "school_id"],
            ["classe.id", "classe.school_id"],
            ondelete="CASCADE",
            name="fk_affectation_classe_school",
        ),
        ForeignKeyConstraint(
            ["id_matiere", "school_id"],
            ["matiere.id", "matiere.school_id"],
            ondelete="CASCADE",
            name="fk_affectation_matiere_school",
        ),
        ForeignKeyConstraint(
            ["id_annee", "school_id"],
            ["annee_scolaire.id", "annee_scolaire.school_id"],
            ondelete="CASCADE",
            name="fk_affectation_annee_school",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    id_enseignant: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_classe: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_matiere: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_annee: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    volume_horaire_hebdo: Mapped[float | None] = mapped_column(Numeric(5, 2))


class Salle(Base):
    __tablename__ = "salle"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    libelle: Mapped[str] = mapped_column(String(50), nullable=False)
    capacite: Mapped[int | None] = mapped_column(Integer)


class CreneauEmploiTemps(Base):
    """Parent-only : isolation via AffectationEnseignant / Salle.school_id."""

    __tablename__ = "creneau_emploi_temps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_affectation: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("affectation_enseignant.id", ondelete="CASCADE"), nullable=False
    )
    id_salle: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("salle.id", ondelete="SET NULL"))
    jour_semaine: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    heure_debut: Mapped[time] = mapped_column(Time, nullable=False)
    heure_fin: Mapped[time] = mapped_column(Time, nullable=False)
