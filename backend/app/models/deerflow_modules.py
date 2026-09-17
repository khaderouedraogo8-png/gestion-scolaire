from __future__ import annotations

"""Modèles Deerflow — modules A/B (admissions, vie scolaire, paie, e-learning…)."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


def _school_id_cascade() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


# ---------------------------------------------------------------------------
# Admissions & fratrie
# ---------------------------------------------------------------------------


class AdmissionDossier(Base):
    __tablename__ = "admission_dossier"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_annee: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    sexe: Mapped[str | None] = mapped_column(String(1))
    date_naissance: Mapped[date | None] = mapped_column(Date)
    lieu_naissance: Mapped[str | None] = mapped_column(String(100))
    telephone_parent: Mapped[str | None] = mapped_column(String(30))
    email_parent: Mapped[str | None] = mapped_column(String(150))
    niveau_demande: Mapped[str | None] = mapped_column(String(50))
    statut: Mapped[str] = mapped_column(String(30), default="brouillon", nullable=False)
    pieces: Mapped[dict | None] = mapped_column(JSONB)
    id_eleve: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Fratrie(Base):
    __tablename__ = "fratrie"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    libelle: Mapped[str | None] = mapped_column(String(120))
    id_parent_principal: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EleveFratrie(Base):
    __tablename__ = "eleve_fratrie"
    __table_args__ = (
        UniqueConstraint("id_eleve", "id_fratrie", name="uq_eleve_fratrie_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    id_fratrie: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fratrie.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class RemiseRegle(Base):
    __tablename__ = "remise_regle"
    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_remise_regle_school_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    libelle: Mapped[str] = mapped_column(String(120), nullable=False)
    type_remise: Mapped[str] = mapped_column(String(20), default="pourcent", nullable=False)
    valeur: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    condition_type: Mapped[str | None] = mapped_column(String(40))
    condition_valeur: Mapped[str | None] = mapped_column(String(80))
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priorite: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Conseil de classe & passage
# ---------------------------------------------------------------------------


class ConseilClasseSession(Base):
    __tablename__ = "conseil_classe_session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_classe: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_trimestre: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    id_annee: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    date_session: Mapped[date] = mapped_column(Date, nullable=False)
    statut: Mapped[str] = mapped_column(String(30), default="planifie", nullable=False)
    pv_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    anime_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DecisionPassage(Base):
    __tablename__ = "decision_passage"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "id_eleve",
            "id_annee",
            name="uq_decision_passage_eleve_annee",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    id_annee: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_session: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conseil_classe_session.id", ondelete="SET NULL"),
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    mention: Mapped[str | None] = mapped_column(String(40))
    commentaire: Mapped[str | None] = mapped_column(Text)
    valide_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    valide_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Absences & décrochage
# ---------------------------------------------------------------------------


class AbsenceJustificatif(Base):
    __tablename__ = "absence_justificatif"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_absence: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    fichier_url: Mapped[str | None] = mapped_column(Text)
    motif: Mapped[str | None] = mapped_column(Text)
    valide: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    valide_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    date_depot: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valide_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AlerteDecrochage(Base):
    __tablename__ = "alerte_decrochage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    type_alerte: Mapped[str] = mapped_column(String(40), nullable=False)
    niveau: Mapped[str] = mapped_column(String(20), default="moyen", nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    statut: Mapped[str] = mapped_column(String(30), default="ouverte", nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    traite_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    traite_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# EDT
# ---------------------------------------------------------------------------


class EdtPublication(Base):
    __tablename__ = "edt_publication"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_annee: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    libelle: Mapped[str | None] = mapped_column(String(80))
    semaine: Mapped[int | None] = mapped_column(Integer)
    date_debut: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    publie_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    publie_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RemplacementEnseignant(Base):
    __tablename__ = "remplacement_enseignant"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_enseignant_absent: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    id_enseignant_remplacant: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    id_creneau: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    date_remplacement: Mapped[date] = mapped_column(Date, nullable=False)
    motif: Mapped[str | None] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(String(30), default="planifie", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Comptabilité & paie
# ---------------------------------------------------------------------------


class EcritureComptable(Base):
    __tablename__ = "ecriture_comptable"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    date_ecriture: Mapped[date] = mapped_column(Date, nullable=False)
    libelle: Mapped[str] = mapped_column(String(200), nullable=False)
    compte_debit: Mapped[str] = mapped_column(String(16), nullable=False)
    compte_credit: Mapped[str] = mapped_column(String(16), nullable=False)
    montant: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(60))
    id_paiement: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    journal: Mapped[str | None] = mapped_column(String(20))
    piece_url: Mapped[str | None] = mapped_column(Text)
    saisi_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaiePeriode(Base):
    __tablename__ = "paie_periode"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    libelle: Mapped[str] = mapped_column(String(80), nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    statut: Mapped[str] = mapped_column(String(30), default="ouverte", nullable=False)
    cloture_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaieLigne(Base):
    __tablename__ = "paie_ligne"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_periode: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paie_periode.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id_utilisateur: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    id_enseignant: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    matricule: Mapped[str | None] = mapped_column(String(40))
    brut: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    retenues: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    net: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Cantine
# ---------------------------------------------------------------------------


class CantineAbonnement(Base):
    __tablename__ = "cantine_abonnement"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    id_annee: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    formule: Mapped[str] = mapped_column(String(40), default="standard", nullable=False)
    montant: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date | None] = mapped_column(Date)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    id_paiement: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CantinePresence(Base):
    __tablename__ = "cantine_presence"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "id_eleve",
            "date_presence",
            "repas",
            name="uq_cantine_presence_eleve_date_repas",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    date_presence: Mapped[date] = mapped_column(Date, nullable=False)
    repas: Mapped[str] = mapped_column(String(20), default="midi", nullable=False)
    present: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class TransportItineraire(Base):
    __tablename__ = "transport_itineraire"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    libelle: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TransportArret(Base):
    __tablename__ = "transport_arret"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_itineraire: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transport_itineraire.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    libelle: Mapped[str] = mapped_column(String(120), nullable=False)
    ordre: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    heure_passage: Mapped[str | None] = mapped_column(String(10))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))


class TransportEleve(Base):
    __tablename__ = "transport_eleve"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    id_itineraire: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transport_itineraire.id", ondelete="CASCADE"),
        nullable=False,
    )
    id_arret: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transport_arret.id", ondelete="SET NULL"),
    )
    id_annee: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TransportPointage(Base):
    __tablename__ = "transport_pointage"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "id_arret",
            "date_pointage",
            "id_eleve",
            name="uq_transport_pointage_arret_date_eleve",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_arret: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transport_arret.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    date_pointage: Mapped[date] = mapped_column(Date, nullable=False)
    embarque: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Internat
# ---------------------------------------------------------------------------


class InternatChambre(Base):
    __tablename__ = "internat_chambre"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "batiment",
            "numero",
            name="uq_internat_chambre_batiment_numero",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    batiment: Mapped[str | None] = mapped_column(String(60))
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    capacite: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    genre: Mapped[str | None] = mapped_column(String(10))
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class InternatAffectation(Base):
    __tablename__ = "internat_affectation"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_chambre: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("internat_chambre.id", ondelete="CASCADE"),
        nullable=False,
    )
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    id_annee: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date | None] = mapped_column(Date)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Infirmerie & bibliothèque
# ---------------------------------------------------------------------------


class InfirmiereSoin(Base):
    __tablename__ = "infirmiere_soin"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    date_soin: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    motif: Mapped[str] = mapped_column(Text, nullable=False)
    traitement: Mapped[str | None] = mapped_column(Text)
    soigne_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BibliothequeLivre(Base):
    __tablename__ = "bibliotheque_livre"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    isbn: Mapped[str | None] = mapped_column(String(20))
    titre: Mapped[str] = mapped_column(String(200), nullable=False)
    auteur: Mapped[str | None] = mapped_column(String(150))
    categorie: Mapped[str | None] = mapped_column(String(60))
    exemplaires: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    disponibles: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BibliothequePret(Base):
    __tablename__ = "bibliotheque_pret"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_livre: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bibliotheque_livre.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    date_pret: Mapped[date] = mapped_column(Date, nullable=False)
    date_retour_prevue: Mapped[date | None] = mapped_column(Date)
    date_retour_effective: Mapped[date | None] = mapped_column(Date)
    statut: Mapped[str] = mapped_column(String(20), default="en_cours", nullable=False)
    amende: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# RH
# ---------------------------------------------------------------------------


class RhContrat(Base):
    __tablename__ = "rh_contrat"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_utilisateur: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    id_enseignant: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    type_contrat: Mapped[str] = mapped_column(String(40), nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date | None] = mapped_column(Date)
    salaire_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    statut: Mapped[str] = mapped_column(String(30), default="actif", nullable=False)
    poste: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RhConge(Base):
    __tablename__ = "rh_conge"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_utilisateur: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    type_conge: Mapped[str] = mapped_column(String(40), nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    statut: Mapped[str] = mapped_column(String(30), default="demande", nullable=False)
    motif: Mapped[str | None] = mapped_column(Text)
    valide_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    valide_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Vie scolaire
# ---------------------------------------------------------------------------


class Visiteur(Base):
    __tablename__ = "visiteur"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str | None] = mapped_column(String(100))
    motif: Mapped[str | None] = mapped_column(Text)
    piece_identite: Mapped[str | None] = mapped_column(String(60))
    telephone: Mapped[str | None] = mapped_column(String(30))
    heure_entree: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    heure_sortie: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accueilli_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    id_eleve_visite: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class SortieEleve(Base):
    __tablename__ = "sortie_eleve"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    date_sortie: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    motif: Mapped[str | None] = mapped_column(Text)
    autorise_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    recupere_par: Mapped[str | None] = mapped_column(String(150))
    heure_retour: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    statut: Mapped[str] = mapped_column(String(20), default="sorti", nullable=False)
    token_hmac: Mapped[str | None] = mapped_column(String(128))
    parent_valide: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_valide_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Inventaire
# ---------------------------------------------------------------------------


class InventaireArticle(Base):
    __tablename__ = "inventaire_article"
    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_inventaire_article_school_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    libelle: Mapped[str] = mapped_column(String(150), nullable=False)
    categorie: Mapped[str | None] = mapped_column(String(60))
    quantite: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seuil_alerte: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unite: Mapped[str | None] = mapped_column(String(20))
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventaireMouvement(Base):
    __tablename__ = "inventaire_mouvement"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_article: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventaire_article.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type_mouvement: Mapped[str] = mapped_column(String(20), nullable=False)
    quantite: Mapped[int] = mapped_column(Integer, nullable=False)
    motif: Mapped[str | None] = mapped_column(Text)
    date_mouvement: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    effectue_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


# ---------------------------------------------------------------------------
# E-learning
# ---------------------------------------------------------------------------


class ElearningDevoir(Base):
    __tablename__ = "elearning_devoir"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_classe: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    id_matiere: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    titre: Mapped[str] = mapped_column(String(200), nullable=False)
    consignes: Mapped[str | None] = mapped_column(Text)
    date_limite: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cree_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    publie: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ElearningRemise(Base):
    __tablename__ = "elearning_remise"
    __table_args__ = (
        UniqueConstraint("id_devoir", "id_eleve", name="uq_elearning_remise_devoir_eleve"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_devoir: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("elearning_devoir.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id_eleve: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    fichier_url: Mapped[str | None] = mapped_column(Text)
    contenu: Mapped[str | None] = mapped_column(Text)
    date_remise: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    note: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    commentaire: Mapped[str | None] = mapped_column(Text)


class ElearningQuiz(Base):
    __tablename__ = "elearning_quiz"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    id_classe: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    id_matiere: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    titre: Mapped[str] = mapped_column(String(200), nullable=False)
    questions: Mapped[dict | list | None] = mapped_column(JSONB)
    duree_minutes: Mapped[int | None] = mapped_column(Integer)
    publie: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cree_par: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------------


class OtpChallenge(Base):
    __tablename__ = "otp_challenge"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = _school_id_cascade()
    canal: Mapped[str] = mapped_column(String(20), nullable=False)
    destinataire: Mapped[str] = mapped_column(String(150), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(String(40), default="login", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    id_utilisateur: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
