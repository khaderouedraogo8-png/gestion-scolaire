from __future__ import annotations

"""Modèles utilisateurs, tokens et réinitialisation MDP."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import Base

# Rôles rattachés à une école (school_id NOT NULL)
SCHOOL_ROLES = (
    "administrateur",
    "directeur",
    "enseignant",
    "agent_comptable",
    "secretariat",
    "parent",
)

# Rôle plateforme SaaS (school_id IS NULL)
PLATFORM_ROLE_SUPER_ADMIN = "super_admin"
PLATFORM_ROLES = (PLATFORM_ROLE_SUPER_ADMIN,)

# Tous les rôles connus
ROLES = SCHOOL_ROLES + PLATFORM_ROLES


class Utilisateur(Base):
    __tablename__ = "utilisateur"
    __table_args__ = (
        CheckConstraint(
            "(role = 'super_admin' AND school_id IS NULL) OR "
            "(role <> 'super_admin' AND school_id IS NOT NULL)",
            name="ck_utilisateur_super_admin_school",
        ),
    )

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
    # Tenant SaaS — NULL uniquement pour super_admin (PR #10)
    school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    school = relationship("School", foreign_keys=[school_id])


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
