"""Services plateforme — onboarding écoles et gestion SUPER_ADMIN."""
from __future__ import annotations

import re
import uuid

from flask import abort
from sqlalchemy.exc import IntegrityError

from app.auth.jwt_handler import hash_password
from app.extensions import get_db
from app.models import Etablissement, School, Utilisateur
from app.models.utilisateur import PLATFORM_ROLE_SUPER_ADMIN, SCHOOL_ROLES
from app.utils.audit_logger import log_audit

CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,48}[A-Z0-9]$", re.IGNORECASE)


def normalize_school_code(code: str) -> str:
    return (code or "").strip().upper()


def validate_school_code(code: str) -> str:
    normalized = normalize_school_code(code)
    if not normalized or len(normalized) < 2 or len(normalized) > 50:
        abort(400, description="Code école invalide (2–50 caractères).")
    if not CODE_RE.match(normalized):
        abort(400, description="Code école : lettres, chiffres, tirets et underscores uniquement.")
    return normalized


def count_active_admins(school_id: uuid.UUID) -> int:
    db = get_db()
    return (
        db.query(Utilisateur)
        .filter(
            Utilisateur.school_id == school_id,
            Utilisateur.role == "administrateur",
            Utilisateur.actif.is_(True),
        )
        .count()
    )


def count_active_super_admins() -> int:
    db = get_db()
    return (
        db.query(Utilisateur)
        .filter(
            Utilisateur.role == PLATFORM_ROLE_SUPER_ADMIN,
            Utilisateur.actif.is_(True),
            Utilisateur.school_id.is_(None),
        )
        .count()
    )


def ensure_not_last_school_admin(user: Utilisateur) -> None:
    """Refuse de désactiver / dé-rôler le dernier administrateur actif d'une école."""
    if user.role != "administrateur" or not user.actif or not user.school_id:
        return
    if count_active_admins(user.school_id) <= 1:
        abort(409, description="Impossible de désactiver ou modifier le dernier administrateur actif.")


def ensure_not_last_super_admin(user: Utilisateur) -> None:
    if user.role != PLATFORM_ROLE_SUPER_ADMIN or not user.actif:
        return
    if count_active_super_admins() <= 1:
        abort(409, description="Impossible de désactiver le dernier SUPER_ADMIN.")


def onboard_school(
    *,
    actor: Utilisateur,
    name: str,
    code: str,
    admin_nom: str,
    admin_prenom: str,
    admin_email: str,
    admin_password: str,
    admin_telephone: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    address: str | None = None,
    city: str | None = None,
    country: str | None = None,
    logo: str | None = None,
    activate: bool = True,
) -> tuple[School, Utilisateur, Etablissement]:
    """
    Onboarding atomique : School + Etablissement 1:1 + premier administrateur.
    Rollback total en cas d'échec.
    """
    db = get_db()
    code_norm = validate_school_code(code)
    name = (name or "").strip()
    if not name:
        abort(400, description="Le nom de l'école est obligatoire.")

    admin_email = (admin_email or "").strip().lower()
    if db.query(School).filter(School.code == code_norm).first():
        abort(409, description="Code école déjà utilisé.")
    if db.query(Utilisateur).filter(Utilisateur.email == admin_email).first():
        abort(409, description="Email administrateur déjà utilisé.")

    school = School(
        id=uuid.uuid4(),
        name=name,
        code=code_norm,
        email=email,
        phone=phone,
        address=address,
        city=city,
        country=country,
        logo=logo,
        is_active=bool(activate),
        created_by=actor.id if actor else None,
    )
    etab = Etablissement(
        id=uuid.uuid4(),
        school_id=school.id,
        nom=name,
        email=email,
        telephone=phone,
        adresse=address,
        ville=city,
        pays=country,
        logo_url=logo,
        format_matricule="{ANNEE}M-{SEQ}",
        devise="XOF",
    )
    admin = Utilisateur(
        id=uuid.uuid4(),
        nom=admin_nom.strip(),
        prenom=admin_prenom.strip(),
        email=admin_email,
        telephone=admin_telephone,
        role="administrateur",
        mot_de_passe_hash=hash_password(admin_password),
        actif=True,
        doit_changer_mdp=True,
        school_id=school.id,
    )

    try:
        db.add(school)
        db.flush()
        db.add(etab)
        db.add(admin)
        db.commit()
    except IntegrityError:
        db.rollback()
        abort(409, description="Conflit d'unicité lors de l'onboarding (code ou email).")
    except Exception:
        db.rollback()
        raise

    log_audit(
        "SCHOOL_CREATED",
        actor.id if actor else None,
        "schools",
        school.id,
        details={"name": school.name, "code": school.code},
        school_id=school.id,
    )
    log_audit(
        "ETABLISSEMENT_CREATED",
        actor.id if actor else None,
        "etablissement",
        etab.id,
        details={"nom": etab.nom},
        school_id=school.id,
    )
    log_audit(
        "ADMIN_CREATED",
        actor.id if actor else None,
        "utilisateur",
        admin.id,
        details={"email": admin.email, "role": admin.role},
        school_id=school.id,
    )
    if school.is_active:
        log_audit(
            "SCHOOL_ACTIVATED",
            actor.id if actor else None,
            "schools",
            school.id,
            school_id=school.id,
        )

    return school, admin, etab


def create_school_admin(
    *,
    actor: Utilisateur,
    school: School,
    nom: str,
    prenom: str,
    email: str,
    password: str,
    telephone: str | None = None,
) -> Utilisateur:
    """Ajoute un administrateur à une école existante (platform only)."""
    db = get_db()
    email_n = email.strip().lower()
    if db.query(Utilisateur).filter(Utilisateur.email == email_n).first():
        abort(409, description="Email déjà utilisé.")
    user = Utilisateur(
        id=uuid.uuid4(),
        nom=nom.strip(),
        prenom=prenom.strip(),
        email=email_n,
        telephone=telephone,
        role="administrateur",
        mot_de_passe_hash=hash_password(password),
        actif=True,
        doit_changer_mdp=True,
        school_id=school.id,
    )
    db.add(user)
    db.commit()
    log_audit(
        "ADMIN_CREATED",
        actor.id,
        "utilisateur",
        user.id,
        details={"email": user.email, "role": user.role},
        school_id=school.id,
    )
    return user


def assert_school_role(role: str) -> str:
    if role not in SCHOOL_ROLES:
        abort(400, description="Rôle école invalide.")
    if role == PLATFORM_ROLE_SUPER_ADMIN:
        abort(403, description="Promotion SUPER_ADMIN interdite via API.")
    return role
