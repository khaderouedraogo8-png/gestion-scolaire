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
from app.models.utilisateur import PLATFORM_ROLE_SUPER_ADMIN
from app.services.tenant import is_super_admin


def require_role(*roles):
    """
    Décorateur RBAC : exige que l'utilisateur authentifié possède l'un des rôles listés.
    Usage : @require_role('directeur', 'administrateur')

    La vérification utilise le rôle en base (get_current_user), pas le claim JWT seul.
    Un super_admin avec acting_school_id valide est autorisé (support plateforme).
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = get_current_user()
            if not user or not user.actif:
                return jsonify({"message": "Non authentifié"}), 401
            if is_super_admin(user):
                # Métier uniquement avec contexte école explicite
                from app.services.tenant import resolve_effective_school_id

                resolve_effective_school_id(require=True)
                return fn(*args, **kwargs)
            if user.role not in roles:
                return jsonify({"message": "Accès refusé — rôle insuffisant"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def require_super_admin(fn):
    """
    Exige le rôle plateforme super_admin (school_id IS NULL en DB).
    Ne se fie jamais au seul claim JWT.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if not user or not user.actif:
            return jsonify({"message": "Non authentifié"}), 401
        if not is_super_admin(user) or user.role != PLATFORM_ROLE_SUPER_ADMIN:
            return jsonify({"message": "Accès réservé au SUPER_ADMIN plateforme"}), 403
        return fn(*args, **kwargs)

    return wrapper


def _has_admin_like_access(user) -> bool:
    """Admin école, directeur, ou SUPER_ADMIN en contexte école."""
    if not user:
        return False
    if user.role in ("administrateur", "directeur"):
        return True
    return is_super_admin(user)


def get_enseignant_for_user(user) -> Enseignant | None:
    """Retourne l'entité enseignant liée à l'utilisateur (même école)."""
    if not user:
        return None
    db = get_db()
    q = db.query(Enseignant).filter(Enseignant.id_utilisateur == user.id)
    if user.school_id:
        q = q.filter(Enseignant.school_id == user.school_id)
    return q.first()


def teacher_has_class_access(user, id_classe: uuid.UUID) -> bool:
    """Vérifie qu'un enseignant est affecté à la classe donnée."""
    if _has_admin_like_access(user):
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
            AffectationEnseignant.school_id == enseignant.school_id,
            AffectationEnseignant.id_enseignant == enseignant.id,
            AffectationEnseignant.id_classe == id_classe,
        )
        .first()
    )
    return affectation is not None


def teacher_has_matiere_classe_access(user, id_classe: uuid.UUID, id_matiere: uuid.UUID) -> bool:
    """Vérifie l'affectation enseignant/classe/matière."""
    if _has_admin_like_access(user):
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
            AffectationEnseignant.school_id == enseignant.school_id,
            AffectationEnseignant.id_enseignant == enseignant.id,
            AffectationEnseignant.id_classe == id_classe,
            AffectationEnseignant.id_matiere == id_matiere,
        )
        .first()
    )
    return affectation is not None


def parent_has_eleve_access(user, id_eleve: uuid.UUID) -> bool:
    """Vérifie qu'un parent a accès à la fiche de son enfant."""
    if _has_admin_like_access(user) or user.role == "secretariat":
        return True
    if user.role != "parent":
        return False
    db = get_db()
    q = db.query(ParentTuteur).filter(ParentTuteur.id_utilisateur == user.id)
    if user.school_id:
        q = q.filter(ParentTuteur.school_id == user.school_id)
    parent = q.first()
    if not parent:
        return False
    link = (
        db.query(EleveParent)
        .filter(EleveParent.id_parent == parent.id, EleveParent.id_eleve == id_eleve)
        .first()
    )
    if not link:
        return False
    # Anti cross-tenant : l'élève doit être de la même école
    eleve = db.query(Eleve).filter(Eleve.id == id_eleve, Eleve.school_id == parent.school_id).first()
    return eleve is not None


def teacher_has_eleve_access(user, id_eleve: uuid.UUID) -> bool:
    """Vérifie qu'un enseignant est affecté à une classe où l'élève est inscrit."""
    if _has_admin_like_access(user) or user.role in ("secretariat", "agent_comptable"):
        return True
    if user.role != "enseignant":
        return False
    class_ids = get_teacher_class_ids(user)
    if not class_ids:
        return False
    db = get_db()
    q = db.query(Inscription).filter(
        Inscription.id_eleve == id_eleve,
        Inscription.id_classe.in_(class_ids),
        Inscription.statut.in_(("inscrit", "reinscrit")),
    )
    if user.school_id:
        q = q.filter(Inscription.school_id == user.school_id)
    return q.first() is not None


def can_view_medical_notes(user) -> bool:
    """Seuls admin/directeur/secrétariat (ou SUPER_ADMIN en contexte) peuvent voir les notes médicales."""
    return _has_admin_like_access(user) or user.role == "secretariat"


def get_teacher_class_ids(user) -> list[uuid.UUID]:
    """Retourne la liste des IDs de classes accessibles à l'enseignant."""
    if _has_admin_like_access(user) or user.role in ("secretariat", "agent_comptable"):
        return []
    enseignant = get_enseignant_for_user(user)
    if not enseignant:
        return []
    db = get_db()
    affectations = (
        db.query(AffectationEnseignant.id_classe)
        .filter(
            AffectationEnseignant.id_enseignant == enseignant.id,
            AffectationEnseignant.school_id == enseignant.school_id,
        )
        .distinct()
        .all()
    )
    return [a[0] for a in affectations]


def get_parent_eleve_ids(user) -> list[uuid.UUID]:
    """Retourne les IDs élèves accessibles au parent."""
    db = get_db()
    q = db.query(ParentTuteur).filter(ParentTuteur.id_utilisateur == user.id)
    if user.school_id:
        q = q.filter(ParentTuteur.school_id == user.school_id)
    parent = q.first()
    if not parent:
        return []
    links = db.query(EleveParent.id_eleve).filter(EleveParent.id_parent == parent.id).all()
    eleve_ids = [l[0] for l in links]
    if not eleve_ids or not parent.school_id:
        return eleve_ids
    # Restreindre aux élèves de la même école
    rows = (
        db.query(Eleve.id)
        .filter(Eleve.id.in_(eleve_ids), Eleve.school_id == parent.school_id)
        .all()
    )
    return [r[0] for r in rows]


def get_parent_classe_ids(user, id_annee: uuid.UUID | None = None) -> list[uuid.UUID]:
    """Retourne les IDs de classes où le parent a un enfant inscrit."""
    db = get_db()
    eleve_ids = get_parent_eleve_ids(user)
    if not eleve_ids:
        return []
    q = db.query(Inscription.id_classe).filter(
        Inscription.id_eleve.in_(eleve_ids),
        Inscription.statut.in_(("inscrit", "reinscrit")),
    )
    if user.school_id:
        q = q.filter(Inscription.school_id == user.school_id)
    if id_annee:
        q = q.filter(Inscription.id_annee == id_annee)
    return list({row[0] for row in q.distinct().all()})

def parent_has_classe_access(user, id_classe: uuid.UUID, id_annee: uuid.UUID | None = None) -> bool:
    """Vérifie qu'un parent a un enfant inscrit dans la classe."""
    if _has_admin_like_access(user) or user.role == "secretariat":
        return True
    if user.role != "parent":
        return False
    return id_classe in get_parent_classe_ids(user, id_annee)


def filter_eleves_by_role(query, user):
    """Filtre une requête élèves selon le rôle de l'utilisateur."""
    if _has_admin_like_access(user) or user.role in ("secretariat", "agent_comptable"):
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
