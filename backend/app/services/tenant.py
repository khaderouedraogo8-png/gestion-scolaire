"""Contexte tenant multi-école — déterminé uniquement via l'utilisateur authentifié."""
from __future__ import annotations

import uuid
from typing import Any, TypeVar

from flask import abort
from sqlalchemy.orm import Query

from app.auth.jwt_handler import get_current_user
from app.extensions import get_db
from app.models import School, Utilisateur

T = TypeVar("T")


class TenantRequiredError(Exception):
    """Utilisateur authentifié sans école associée."""

    def __init__(self, message: str = "Aucune école associée à cet utilisateur."):
        self.message = message
        super().__init__(message)


def get_current_school_id() -> uuid.UUID:
    """
    Retourne le school_id du tenant courant.

    Source de vérité : utilisateur JWT (jamais un school_id fourni par le client).
    """
    user = get_current_user()
    if not user or not user.actif:
        abort(401)
    if not user.school_id:
        abort(403, description="Aucune école associée à cet utilisateur.")
    return user.school_id


def get_current_school() -> School:
    """Charge l'entité School du tenant courant."""
    school_id = get_current_school_id()
    db = get_db()
    school = db.query(School).filter(School.id == school_id).first()
    if not school or not school.is_active:
        abort(403, description="École introuvable ou inactive.")
    return school


def require_user_school(user: Utilisateur | None) -> uuid.UUID:
    """Helper testable : exige un school_id sur l'utilisateur fourni."""
    if not user:
        raise TenantRequiredError("Utilisateur non authentifié.")
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
