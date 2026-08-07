from __future__ import annotations

"""Modèles utilisateurs, tokens et réinitialisation MDP."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


ROLES = (
    "administrateur",
    "directeur",
    "enseignant",
    "agent_comptable",
    "secretariat",
    "parent",
)


class Utilisateur(Base):
    __tablename__ = "utilisateur"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    telephone: Mapped[str | None] = mapped_column(String(30))
    mot_de_passe_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    doit_changer_mdp: Mapped[bool] = mapped_column(Boolean, default=True)
    derniere_connexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tentatives_echouees: Mapped[int] = mapped_column(SmallInteger, default=0)
    verrouille_jusqu_a: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_utilisateur: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_creation: Mapped[str | None] = mapped_column(INET)
    expire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoque: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReinitialisationMdp(Base):
    __tablename__ = "reinitialisation_mdp"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_utilisateur: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    utilise: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
