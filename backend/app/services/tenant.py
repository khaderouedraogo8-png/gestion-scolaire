"""Contexte tenant multi-école — déterminé uniquement via l'utilisateur authentifié."""
from __future__ import annotations

import uuid

from flask import abort

from app.auth.jwt_handler import get_current_user
from app.extensions import get_db
from app.models import School, Utilisateur


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
