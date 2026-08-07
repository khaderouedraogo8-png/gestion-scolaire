"""RBAC : décorateurs de rôle et vérifications de propriété des données."""
import uuid
from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request

from app.auth.jwt_handler import get_current_user
from app.extensions import get_db
from app.models import (
    AffectationEnseignant,
    Eleve,
    EleveParent,
    Enseignant,
    Inscription,
    ParentTuteur,
)


def require_role(*roles):
    """
    Décorateur RBAC : exige que l'utilisateur authentifié possède l'un des rôles listés.
    Usage : @require_role('directeur', 'administrateur')
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = get_current_user()
            if not user or not user.actif:
                return jsonify({"message": "Non authentifié"}), 401
            if user.role not in roles:
                return jsonify({"message": "Accès refusé — rôle insuffisant"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def get_enseignant_for_user(user) -> Enseignant | None:
    """Retourne l'entité enseignant liée à l'utilisateur."""
    if not user:
        return None
    db = get_db()
    return db.query(Enseignant).filter(Enseignant.id_utilisateur == user.id).first()


def teacher_has_class_access(user, id_classe: uuid.UUID) -> bool:
    """Vérifie qu'un enseignant est affecté à la classe donnée."""
    if user.role in ("administrateur", "directeur"):
        return True
    if user.role != "enseignant":
        return False
    enseignant = get_enseignant_for_user(user)
    if not enseignant:
        return False
    db = get_db()
    affectation = (
        db.query(AffectationEnseignant)
        .filter(
            AffectationEnseignant.id_enseignant == enseignant.id,
            AffectationEnseignant.id_classe == id_classe,
        )
        .first()
    )
    return affectation is not None


def teacher_has_matiere_classe_access(user, id_classe: uuid.UUID, id_matiere: uuid.UUID) -> bool:
    """Vérifie l'affectation enseignant/classe/matière."""
    if user.role in ("administrateur", "directeur"):
        return True
    if user.role != "enseignant":
        return False
    enseignant = get_enseignant_for_user(user)
    if not enseignant:
        return False
    db = get_db()
    affectation = (
        db.query(AffectationEnseignant)
        .filter(
            AffectationEnseignant.id_enseignant == enseignant.id,
            AffectationEnseignant.id_classe == id_classe,
            AffectationEnseignant.id_matiere == id_matiere,
        )
        .first()
    )
    return affectation is not None


def parent_has_eleve_access(user, id_eleve: uuid.UUID) -> bool:
    """Vérifie qu'un parent a accès à la fiche de son enfant."""
    if user.role in ("administrateur", "directeur", "secretariat"):
        return True
    if user.role != "parent":
        return False
    db = get_db()
    parent = db.query(ParentTuteur).filter(ParentTuteur.id_utilisateur == user.id).first()
    if not parent:
        return False
    link = (
        db.query(EleveParent)
        .filter(EleveParent.id_parent == parent.id, EleveParent.id_eleve == id_eleve)
        .first()
    )
    return link is not None


def can_view_medical_notes(user) -> bool:
    """Seuls admin/directeur/secrétariat peuvent voir les notes médicales."""
    return user.role in ("administrateur", "directeur", "secretariat")


def get_teacher_class_ids(user) -> list[uuid.UUID]:
    """Retourne la liste des IDs de classes accessibles à l'enseignant."""
    if user.role in ("administrateur", "directeur", "secretariat", "agent_comptable"):
        return []
    enseignant = get_enseignant_for_user(user)
    if not enseignant:
        return []
    db = get_db()
    affectations = (
        db.query(AffectationEnseignant.id_classe)
        .filter(AffectationEnseignant.id_enseignant == enseignant.id)
        .distinct()
        .all()
    )
    return [a[0] for a in affectations]


def get_parent_eleve_ids(user) -> list[uuid.UUID]:
    """Retourne les IDs élèves accessibles au parent."""
    db = get_db()
    parent = db.query(ParentTuteur).filter(ParentTuteur.id_utilisateur == user.id).first()
    if not parent:
        return []
    links = db.query(EleveParent.id_eleve).filter(EleveParent.id_parent == parent.id).all()
    return [l[0] for l in links]


def filter_eleves_by_role(query, user):
    """Filtre une requête élèves selon le rôle de l'utilisateur."""
    if user.role in ("administrateur", "directeur", "secretariat", "agent_comptable"):
        return query
    if user.role == "enseignant":
        class_ids = get_teacher_class_ids(user)
        if not class_ids:
            return query.filter(Eleve.id.is_(None))
        return query.join(Inscription).filter(Inscription.id_classe.in_(class_ids))
    if user.role == "parent":
        eleve_ids = get_parent_eleve_ids(user)
        if not eleve_ids:
            return query.filter(Eleve.id.is_(None))
        return query.filter(Eleve.id.in_(eleve_ids))
    return query.filter(Eleve.id.is_(None))
