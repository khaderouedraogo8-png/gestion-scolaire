"""Gestion JWT : access token, refresh token avec rotation."""
import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import current_app, request
from flask_jwt_extended import create_access_token, get_jwt_identity

from app.extensions import get_db
from app.models import RefreshToken, School, Utilisateur
from app.models.utilisateur import PLATFORM_ROLE_SUPER_ADMIN

# Paramètres OWASP recommandés pour Argon2id
ph = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash un mot de passe avec Argon2id."""
    return ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Vérifie un mot de passe contre son hash Argon2id."""
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def needs_rehash(password_hash: str) -> bool:
    return ph.check_needs_rehash(password_hash)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def build_access_token_for_user(
    user: Utilisateur,
    *,
    acting_school_id: uuid.UUID | None = None,
) -> str:
    """Access token uniquement (claims rôle + acting_school_id optionnel pour super_admin)."""
    claims: dict = {"role": user.role, "email": user.email}
    if (
        user.role == PLATFORM_ROLE_SUPER_ADMIN
        and user.school_id is None
        and acting_school_id is not None
    ):
        claims["acting_school_id"] = str(acting_school_id)
    return create_access_token(identity=str(user.id), additional_claims=claims)


def create_tokens_for_user(
    user: Utilisateur,
    *,
    acting_school_id: uuid.UUID | None = None,
) -> tuple[str, str, RefreshToken]:
    """
    Crée un access token JWT (15 min) et un refresh token (7 jours).
    Le refresh token est stocké hashé en base pour rotation/révocation.

    acting_school_id : claim temporaire uniquement pour super_admin (school switch).
    """
    access_token = build_access_token_for_user(user, acting_school_id=acting_school_id)

    raw_refresh = secrets.token_urlsafe(64)
    expire_at = datetime.now(UTC) + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]

    db = get_db()
    refresh_record = RefreshToken(
        id=uuid.uuid4(),
        id_utilisateur=user.id,
        token_hash=_hash_token(raw_refresh),
        user_agent=request.headers.get("User-Agent"),
        ip_creation=request.remote_addr,
        expire_at=expire_at,
    )
    db.add(refresh_record)
    db.commit()

    return access_token, raw_refresh, refresh_record


def _school_allows_session(user: Utilisateur) -> bool:
    """False si user école avec école inactive (super_admin toujours True)."""
    if user.role == PLATFORM_ROLE_SUPER_ADMIN and user.school_id is None:
        return True
    if not user.school_id:
        return False
    db = get_db()
    school = db.query(School).filter(School.id == user.school_id).first()
    return bool(school and school.is_active)


def rotate_refresh_token(old_raw_token: str) -> tuple[str, str] | None:
    """
    Rotation du refresh token : révoque l'ancien et en émet un nouveau.
    Retourne (access_token, new_raw_refresh) ou None si invalide.

    Le claim acting_school_id n'est PAS conservé au refresh (re-switch requis).
    """
    db = get_db()
    token_hash = _hash_token(old_raw_token)
    record = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoque.is_(False),
            RefreshToken.expire_at > datetime.now(UTC),
        )
        .first()
    )
    if not record:
        return None

    user = db.query(Utilisateur).filter(Utilisateur.id == record.id_utilisateur).first()
    if not user or not user.actif:
        return None
    if not _school_allows_session(user):
        return None

    # Révoquer l'ancien token (rotation)
    record.revoque = True
    db.commit()

    access_token, new_raw_refresh, _ = create_tokens_for_user(user)
    return access_token, new_raw_refresh


def revoke_refresh_token(raw_token: str) -> bool:
    """Révoque un refresh token (déconnexion)."""
    db = get_db()
    token_hash = _hash_token(raw_token)
    record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if record:
        record.revoque = True
        db.commit()
        return True
    return False


def revoke_all_user_tokens(user_id: uuid.UUID) -> None:
    """Révoque tous les refresh tokens d'un utilisateur."""
    db = get_db()
    db.query(RefreshToken).filter(
        RefreshToken.id_utilisateur == user_id,
        RefreshToken.revoque.is_(False),
    ).update({"revoque": True})
    db.commit()


def get_current_user() -> Utilisateur | None:
    """Retourne l'utilisateur courant depuis le JWT."""
    identity = get_jwt_identity()
    if not identity:
        return None
    db = get_db()
    return db.query(Utilisateur).filter(Utilisateur.id == uuid.UUID(identity)).first()


REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 3600


def set_refresh_cookie(response, raw_refresh: str):
    """Dépose le refresh token en cookie httpOnly sécurisé."""
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        raw_refresh,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=not current_app.debug and not current_app.testing,
        samesite="Strict",
        path="/api",
    )
    return response


def clear_refresh_cookie(response):
    """Supprime le cookie refresh token."""
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api")
    return response


def get_refresh_from_cookie() -> str | None:
    return request.cookies.get(REFRESH_COOKIE_NAME)
