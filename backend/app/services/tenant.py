"""Contexte tenant multi-école — déterminé uniquement via l'utilisateur authentifié (+ acting context SUPER_ADMIN)."""
from __future__ import annotations

import uuid
from typing import Any, TypeVar

from flask import abort
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from sqlalchemy.orm import Query

from app.auth.jwt_handler import get_current_user
from app.extensions import get_db
from app.models import School, Utilisateur
from app.models.utilisateur import PLATFORM_ROLE_SUPER_ADMIN

T = TypeVar("T")


class TenantRequiredError(Exception):
    """Utilisateur authentifié sans école associée."""

    def __init__(self, message: str = "Aucune école associée à cet utilisateur."):
        self.message = message
        super().__init__(message)


def is_super_admin(user: Utilisateur | None) -> bool:
    return bool(user and user.role == PLATFORM_ROLE_SUPER_ADMIN and user.school_id is None)


def _acting_school_id_from_jwt() -> uuid.UUID | None:
    """Lit acting_school_id du JWT access (uniquement pertinent pour super_admin)."""
    try:
        verify_jwt_in_request(optional=True)
        claims = get_jwt() or {}
    except Exception:
        return None
    raw = claims.get("acting_school_id")
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError):
        return None


def resolve_effective_school_id(*, require: bool = True) -> uuid.UUID | None:
    """
    Résout le school_id effectif pour les routes métier.

    - User école : toujours user.school_id (ignorer claim/header client).
    - super_admin : acting_school_id JWT si présent et validé, sinon None.
    - École inactive : bloquée pour users école ; super_admin sans contexte métier.
    """
    user = get_current_user()
    if not user or not user.actif:
        abort(401)

    if is_super_admin(user):
        acting = _acting_school_id_from_jwt()
        if acting is None:
            if require:
                abort(403, description="Contexte école requis pour cette opération.")
            return None
        db = get_db()
        school = db.query(School).filter(School.id == acting).first()
        if not school:
            abort(403, description="École de contexte introuvable.")
        if not school.is_active:
            abort(403, description="École inactive — accès métier refusé.")
        return school.id

    # Utilisateur rattaché à une école — jamais de spoof via claim
    if not user.school_id:
        abort(403, description="Aucune école associée à cet utilisateur.")
    db = get_db()
    school = db.query(School).filter(School.id == user.school_id).first()
    if not school or not school.is_active:
        abort(403, description="École introuvable ou inactive.")
    return user.school_id


def get_current_school_id() -> uuid.UUID:
    """
    Retourne le school_id du tenant courant.

    Source de vérité : utilisateur JWT (+ acting_school_id serveur pour super_admin).
    Jamais un school_id fourni par le client pour un user école.
    """
    sid = resolve_effective_school_id(require=True)
    assert sid is not None
    return sid


def get_current_school() -> School:
    """Charge l'entité School du tenant courant (active)."""
    school_id = get_current_school_id()
    db = get_db()
    school = db.query(School).filter(School.id == school_id, School.is_active.is_(True)).first()
    if not school:
        abort(403, description="École introuvable ou inactive.")
    return school


def require_user_school(user: Utilisateur | None) -> uuid.UUID:
    """Helper testable : exige un school_id sur l'utilisateur fourni (hors super_admin)."""
    if not user:
        raise TenantRequiredError("Utilisateur non authentifié.")
    if is_super_admin(user):
        raise TenantRequiredError("SUPER_ADMIN n'a pas de school_id permanent.")
    if not user.school_id:
        raise TenantRequiredError("Aucune école associée à cet utilisateur.")
    return user.school_id


def tenant_query[T](model: type[T]) -> Query:
    """
    Query filtrée sur le school_id du tenant courant.

    Le modèle doit exposer une colonne `school_id`.
    """
    if not hasattr(model, "school_id"):
        raise TypeError(f"{model.__name__} n'a pas de colonne school_id")
    db = get_db()
    return db.query(model).filter(model.school_id == get_current_school_id())


def get_or_404_tenant[T](model: type[T], entity_id: uuid.UUID | str) -> T:
    """Charge une entité par id + school_id tenant, sinon 404 (anti-IDOR)."""
    if isinstance(entity_id, str):
        try:
            entity_id = uuid.UUID(entity_id)
        except ValueError:
            abort(404)
    obj = tenant_query(model).filter(model.id == entity_id).first()
    if obj is None:
        abort(404)
    return obj


def assert_same_school(*entities: Any, school_id: uuid.UUID | None = None) -> uuid.UUID:
    """
    Vérifie que toutes les entités appartiennent au même tenant.

    Abort 404 si une entité est absente ou d'un autre school_id (pas de 403 leak).
    """
    expected = school_id or get_current_school_id()
    for entity in entities:
        if entity is None:
            abort(404)
        entity_school = getattr(entity, "school_id", None)
        if entity_school is None or entity_school != expected:
            abort(404)
    return expected


def apply_tenant_school(entity: Any, school_id: uuid.UUID | None = None) -> Any:
    """Assigne school_id au create — ignore toute valeur client éventuelle."""
    sid = school_id or get_current_school_id()
    if not hasattr(entity, "school_id"):
        raise TypeError(f"{type(entity).__name__} n'a pas de colonne school_id")
    entity.school_id = sid
    return entity


def reject_client_school_id(payload: dict | None) -> None:
    """Refuse explicitement un school_id fourni par le client (spoof)."""
    if not payload:
        return
    if "school_id" in payload or "schoolId" in payload:
        abort(400, description="school_id ne peut pas être fourni par le client.")


def assert_school_active_for_login(user: Utilisateur) -> None:
    """Bloque le login des users école si l'école est inactive. super_admin exempt."""
    if is_super_admin(user):
        return
    if not user.school_id:
        abort(403, description="Aucune école associée à cet utilisateur.")
    db = get_db()
    school = db.query(School).filter(School.id == user.school_id).first()
    if not school or not school.is_active:
        abort(403, description="École inactive — connexion refusée.")
