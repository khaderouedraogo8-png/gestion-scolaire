"""Services fondation académique — Program + AcademicPeriod (source de vérité unique)."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from flask import abort
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.jwt_handler import get_current_user
from app.models.etablissement import (
    PROGRAM_CODE_GENERAL,
    PROGRAM_NAME_GENERAL,
    AcademicPeriod,
    AnneeScolaire,
    Classe,
    NiveauEtude,
    Program,
)
from app.services.tenant import (
    apply_tenant_school,
    get_current_school_id,
    get_or_404_tenant,
    is_super_admin,
    reject_client_school_id,
    tenant_query,
)
from app.utils.audit_logger import log_audit

PERIOD_TYPES = frozenset({"trimestre", "semestre", "custom", "annuel"})
PROGRAM_TYPES = frozenset({"general", "technique", "professionnel", "custom"})
PATCHABLE_PROGRAM_FIELDS = frozenset(
    {"code", "name", "description", "program_type", "period_type_default", "is_active"}
)
PATCHABLE_PERIOD_FIELDS = frozenset(
    {
        "id_annee",
        "id_program",
        "sequence",
        "code",
        "label",
        "period_type",
        "date_debut",
        "date_fin",
        "is_active",
    }
)


# ---------------------------------------------------------------------------
# Helpers GENERAL / legacy builders (étape 1)
# ---------------------------------------------------------------------------


def get_or_create_general_program(db: Session, school_id: uuid.UUID) -> Program:
    """Retourne le Program GENERAL de l'école (compatibilité historique permanente)."""
    program = (
        db.query(Program)
        .filter(Program.school_id == school_id, Program.code == PROGRAM_CODE_GENERAL)
        .first()
    )
    if program:
        return program
    program = Program(
        id=uuid.uuid4(),
        school_id=school_id,
        code=PROGRAM_CODE_GENERAL,
        name=PROGRAM_NAME_GENERAL,
        description="Programme de compatibilité historique (données pré-PR11).",
        program_type="general",
        period_type_default="trimestre",
        is_active=True,
    )
    db.add(program)
    db.flush()
    return program


def period_code_and_label(sequence: int, period_type: str = "trimestre") -> tuple[str, str]:
    if period_type == "semestre":
        return f"S{sequence}", f"Semestre {sequence}"
    if period_type == "annuel":
        return "AN", "Année"
    if period_type == "custom":
        return f"P{sequence}", f"Période {sequence}"
    return f"T{sequence}", f"Trimestre {sequence}"


def build_legacy_period(
    *,
    id_annee: uuid.UUID,
    school_id: uuid.UUID,
    id_program: uuid.UUID,
    sequence: int,
    date_debut,
    date_fin,
    period_id: uuid.UUID | None = None,
    period_type: str = "trimestre",
    code: str | None = None,
    label: str | None = None,
) -> AcademicPeriod:
    default_code, default_label = period_code_and_label(sequence, period_type)
    return AcademicPeriod(
        id=period_id or uuid.uuid4(),
        school_id=school_id,
        id_annee=id_annee,
        id_program=id_program,
        sequence=sequence,
        code=code or default_code,
        label=label or default_label,
        period_type=period_type,
        date_debut=date_debut,
        date_fin=date_fin,
        is_active=True,
    )


def resolve_period_school_and_program(
    db: Session,
    id_annee: uuid.UUID,
    id_program: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == id_annee).first()
    if annee is None:
        raise ValueError("Année scolaire introuvable")
    if id_program is not None:
        program = (
            db.query(Program)
            .filter(Program.id == id_program, Program.school_id == annee.school_id)
            .first()
        )
        if program is None:
            raise ValueError("Programme introuvable pour cette école")
        return annee.school_id, program.id
    general = get_or_create_general_program(db, annee.school_id)
    return annee.school_id, general.id


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _audit(action: str, table: str, resource_id: uuid.UUID, *, details: dict | None = None) -> None:
    user = get_current_user()
    payload = dict(details or {})
    if user and is_super_admin(user):
        payload["actor_type"] = "platform_support"
    log_audit(
        action,
        user.id if user else None,
        table,
        resource_id,
        details=payload or None,
        school_id=get_current_school_id(),
    )


def _conflict(message: str) -> None:
    abort(409, description=message)


def _bad_request(message: str) -> None:
    abort(400, description=message)


def _parse_bool_arg(raw: str | None) -> bool | None:
    if raw is None or raw == "":
        return None
    return raw.strip().lower() in ("1", "true", "yes", "oui")


# ---------------------------------------------------------------------------
# Program service
# ---------------------------------------------------------------------------


def list_programs(
    db: Session,
    *,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 25,
) -> tuple[list[dict], int, int]:
    q = tenant_query(Program)
    if is_active is not None:
        q = q.filter(Program.is_active.is_(is_active))
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(or_(Program.code.ilike(term), Program.name.ilike(term)))
    q = q.order_by(Program.code.asc())
    total = q.count()
    pages = max((total + per_page - 1) // per_page, 1) if total else 0
    rows = q.offset((page - 1) * per_page).limit(per_page).all()
    return [serialize_program(db, p, with_counts=True) for p in rows], total, pages


def get_program(db: Session, program_id: uuid.UUID, *, with_counts: bool = True) -> dict:
    program = get_or_404_tenant(Program, program_id)
    return serialize_program(db, program, with_counts=with_counts)


def create_program(db: Session, data: dict) -> dict:
    reject_client_school_id(data)
    code = (data.get("code") or "").strip().upper()
    name = (data.get("name") or "").strip()
    if not code or not name:
        _bad_request("code et name sont obligatoires.")
    program_type = (data.get("program_type") or "general").strip().lower()
    if program_type not in PROGRAM_TYPES:
        _bad_request(f"program_type invalide. Valeurs : {', '.join(sorted(PROGRAM_TYPES))}.")
    period_type_default = (data.get("period_type_default") or "trimestre").strip().lower()
    if period_type_default not in PERIOD_TYPES:
        _bad_request(
            f"period_type_default invalide. Valeurs : {', '.join(sorted(PERIOD_TYPES))}."
        )

    if tenant_query(Program).filter(Program.code == code).first():
        _conflict(f"Un programme avec le code « {code} » existe déjà.")

    program = apply_tenant_school(
        Program(
            id=uuid.uuid4(),
            code=code,
            name=name,
            description=data.get("description"),
            program_type=program_type,
            period_type_default=period_type_default,
            is_active=bool(data.get("is_active", True)),
        )
    )
    db.add(program)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _conflict(f"Un programme avec le code « {code} » existe déjà.")
    _audit("PROGRAM_CREATED", "program", program.id, details={"code": program.code})
    return serialize_program(db, program, with_counts=True)


def update_program(db: Session, program_id: uuid.UUID, data: dict) -> dict:
    reject_client_school_id(data)
    program = get_or_404_tenant(Program, program_id)
    payload = {k: v for k, v in data.items() if k in PATCHABLE_PROGRAM_FIELDS}
    if not payload:
        return serialize_program(db, program, with_counts=True)

    if "code" in payload:
        code = (payload["code"] or "").strip().upper()
        if not code:
            _bad_request("code invalide.")
        if program.code == PROGRAM_CODE_GENERAL and code != PROGRAM_CODE_GENERAL:
            _conflict("Le code GENERAL du programme historique ne peut pas être modifié.")
        dup = (
            tenant_query(Program)
            .filter(Program.code == code, Program.id != program.id)
            .first()
        )
        if dup:
            _conflict(f"Un programme avec le code « {code} » existe déjà.")
        payload["code"] = code
    if "name" in payload:
        name = (payload["name"] or "").strip()
        if not name:
            _bad_request("name invalide.")
        payload["name"] = name
    if "program_type" in payload:
        pt = (payload["program_type"] or "").strip().lower()
        if pt not in PROGRAM_TYPES:
            _bad_request(f"program_type invalide. Valeurs : {', '.join(sorted(PROGRAM_TYPES))}.")
        payload["program_type"] = pt
    if "period_type_default" in payload:
        ptd = (payload["period_type_default"] or "").strip().lower()
        if ptd not in PERIOD_TYPES:
            _bad_request(
                f"period_type_default invalide. Valeurs : {', '.join(sorted(PERIOD_TYPES))}."
            )
        payload["period_type_default"] = ptd

    for key, value in payload.items():
        setattr(program, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _conflict("Conflit d'unicité sur le programme.")
    _audit("PROGRAM_UPDATED", "program", program.id, details={"changed": list(payload.keys())})
    return serialize_program(db, program, with_counts=True)


def deactivate_program(db: Session, program_id: uuid.UUID) -> dict:
    program = get_or_404_tenant(Program, program_id)
    deps = program_dependency_counts(db, program.id)
    if program.code == PROGRAM_CODE_GENERAL:
        _conflict(
            "Le programme GENERAL (compatibilité historique) ne peut pas être désactivé."
        )
    program.is_active = False
    db.commit()
    _audit(
        "PROGRAM_DEACTIVATED",
        "program",
        program.id,
        details={"code": program.code, "dependencies": deps},
    )
    result = serialize_program(db, program, with_counts=True)
    result["dependencies"] = deps
    result["message"] = (
        "Programme désactivé (soft). Les dépendances existantes sont conservées."
    )
    return result


def program_dependency_counts(db: Session, program_id: uuid.UUID) -> dict[str, int]:
    return {
        "levels_count": (
            db.query(func.count(NiveauEtude.id))
            .filter(NiveauEtude.id_program == program_id)
            .scalar()
            or 0
        ),
        "classes_count": (
            db.query(func.count(Classe.id)).filter(Classe.id_program == program_id).scalar() or 0
        ),
        "periods_count": (
            db.query(func.count(AcademicPeriod.id))
            .filter(AcademicPeriod.id_program == program_id)
            .scalar()
            or 0
        ),
    }


def serialize_program(db: Session, program: Program, *, with_counts: bool = False) -> dict:
    data = {
        "id": str(program.id),
        "code": program.code,
        "name": program.name,
        "description": program.description,
        "program_type": program.program_type,
        "period_type_default": program.period_type_default,
        "is_active": program.is_active,
        "created_at": program.created_at.isoformat() if program.created_at else None,
        "updated_at": program.updated_at.isoformat() if program.updated_at else None,
    }
    if with_counts:
        counts = program_dependency_counts(db, program.id)
        data["levels_count"] = counts["levels_count"]
        data["classes_count"] = counts["classes_count"]
        data["periods_count"] = counts["periods_count"]
    return data


# ---------------------------------------------------------------------------
# AcademicPeriod service (/periodes + façade /trimestres)
# ---------------------------------------------------------------------------


def list_periods(
    db: Session,
    *,
    id_program: uuid.UUID | None = None,
    id_annee: uuid.UUID | None = None,
    period_type: str | None = None,
    is_active: bool | None = None,
    page: int | None = None,
    per_page: int | None = None,
) -> tuple[list[AcademicPeriod], int | None, int | None]:
    q = tenant_query(AcademicPeriod)
    if id_program is not None:
        get_or_404_tenant(Program, id_program)
        q = q.filter(AcademicPeriod.id_program == id_program)
    if id_annee is not None:
        get_or_404_tenant(AnneeScolaire, id_annee)
        q = q.filter(AcademicPeriod.id_annee == id_annee)
    if period_type:
        if period_type not in PERIOD_TYPES:
            _bad_request(f"period_type invalide. Valeurs : {', '.join(sorted(PERIOD_TYPES))}.")
        q = q.filter(AcademicPeriod.period_type == period_type)
    if is_active is not None:
        q = q.filter(AcademicPeriod.is_active.is_(is_active))
    q = q.order_by(AcademicPeriod.id_annee, AcademicPeriod.id_program, AcademicPeriod.sequence)
    if page is None or per_page is None:
        return q.all(), None, None
    total = q.count()
    pages = max((total + per_page - 1) // per_page, 1) if total else 0
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return items, total, pages


def get_period(db: Session, period_id: uuid.UUID) -> AcademicPeriod:
    return get_or_404_tenant(AcademicPeriod, period_id)


def _validate_period_payload(data: dict, *, partial: bool = False) -> dict:
    payload: dict[str, Any] = {}
    required = {"id_annee", "id_program", "sequence", "date_debut", "date_fin"}
    for key in PATCHABLE_PERIOD_FIELDS:
        if key in data:
            payload[key] = data[key]
        elif not partial and key in required:
            _bad_request(f"Champ obligatoire manquant : {key}")

    if "sequence" in payload:
        try:
            seq = int(payload["sequence"])
        except (TypeError, ValueError):
            _bad_request("sequence doit être un entier ≥ 1.")
        if seq < 1:
            _bad_request("sequence doit être ≥ 1.")
        payload["sequence"] = seq

    if "period_type" in payload and payload["period_type"] is not None:
        pt = str(payload["period_type"]).strip().lower()
        if pt not in PERIOD_TYPES:
            _bad_request(f"period_type invalide. Valeurs : {', '.join(sorted(PERIOD_TYPES))}.")
        payload["period_type"] = pt

    if "date_debut" in payload and "date_fin" in payload and payload["date_fin"] < payload["date_debut"]:
        _bad_request("date_fin doit être ≥ date_debut.")

    if "code" in payload and payload["code"] is not None:
        payload["code"] = str(payload["code"]).strip().upper()
        if not payload["code"]:
            _bad_request("code invalide.")
    if "label" in payload and payload["label"] is not None:
        payload["label"] = str(payload["label"]).strip()
        if not payload["label"]:
            _bad_request("label invalide.")

    return payload


def _normalize_period_input(data: dict) -> dict:
    raw = dict(data)
    if "numero" in raw and "sequence" not in raw:
        raw["sequence"] = raw.pop("numero")
    elif "numero" in raw:
        raw.pop("numero")
    if "program_id" in raw and "id_program" not in raw:
        raw["id_program"] = raw.pop("program_id")
    if "academic_year_id" in raw and "id_annee" not in raw:
        raw["id_annee"] = raw.pop("academic_year_id")
    return raw


def create_period(db: Session, data: dict) -> AcademicPeriod:
    """Crée une AcademicPeriod — utilisée par /periodes et /trimestres."""
    reject_client_school_id(data)
    raw = _normalize_period_input(data)

    if not raw.get("id_annee"):
        _bad_request("Champ obligatoire manquant : id_annee")
    annee = get_or_404_tenant(AnneeScolaire, raw["id_annee"])

    if not raw.get("id_program"):
        raw["id_program"] = get_or_create_general_program(db, annee.school_id).id

    payload = _validate_period_payload(raw, partial=False)
    program = get_or_404_tenant(Program, payload["id_program"])
    if annee.school_id != program.school_id:
        abort(404)

    period_type = payload.get("period_type") or program.period_type_default or "trimestre"
    if period_type not in PERIOD_TYPES:
        period_type = "trimestre"
    sequence = payload["sequence"]
    default_code, default_label = period_code_and_label(sequence, period_type)
    code = payload.get("code") or default_code
    label = payload.get("label") or default_label

    if (
        tenant_query(AcademicPeriod)
        .filter(
            AcademicPeriod.id_annee == annee.id,
            AcademicPeriod.id_program == program.id,
            AcademicPeriod.sequence == sequence,
        )
        .first()
    ):
        _conflict("Une période avec cette sequence existe déjà pour ce programme et cette année.")
    if (
        tenant_query(AcademicPeriod)
        .filter(
            AcademicPeriod.id_annee == annee.id,
            AcademicPeriod.id_program == program.id,
            AcademicPeriod.code == code,
        )
        .first()
    ):
        _conflict("Une période avec ce code existe déjà pour ce programme et cette année.")

    period = AcademicPeriod(
        id=uuid.uuid4(),
        school_id=annee.school_id,
        id_annee=annee.id,
        id_program=program.id,
        sequence=sequence,
        code=code,
        label=label,
        period_type=period_type,
        date_debut=payload["date_debut"],
        date_fin=payload["date_fin"],
        is_active=bool(payload.get("is_active", True)),
    )
    db.add(period)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _conflict("Conflit d'unicité sur la période académique.")
    _audit(
        "PERIOD_CREATED",
        "academic_period",
        period.id,
        details={
            "code": period.code,
            "sequence": period.sequence,
            "period_type": period.period_type,
        },
    )
    return period


def update_period(db: Session, period_id: uuid.UUID, data: dict) -> AcademicPeriod:
    reject_client_school_id(data)
    period = get_or_404_tenant(AcademicPeriod, period_id)
    raw = _normalize_period_input(data)
    payload = _validate_period_payload(raw, partial=True)
    if not payload:
        return period

    id_annee = payload.get("id_annee", period.id_annee)
    id_program = payload.get("id_program", period.id_program)
    annee = get_or_404_tenant(AnneeScolaire, id_annee)
    program = get_or_404_tenant(Program, id_program)
    if annee.school_id != program.school_id:
        abort(404)

    sequence = payload.get("sequence", period.sequence)
    code = payload.get("code", period.code)
    date_debut = payload.get("date_debut", period.date_debut)
    date_fin = payload.get("date_fin", period.date_fin)
    if date_fin < date_debut:
        _bad_request("date_fin doit être ≥ date_debut.")

    if (
        tenant_query(AcademicPeriod)
        .filter(
            AcademicPeriod.id_annee == annee.id,
            AcademicPeriod.id_program == program.id,
            AcademicPeriod.sequence == sequence,
            AcademicPeriod.id != period.id,
        )
        .first()
    ):
        _conflict("Une période avec cette sequence existe déjà pour ce programme et cette année.")
    if (
        tenant_query(AcademicPeriod)
        .filter(
            AcademicPeriod.id_annee == annee.id,
            AcademicPeriod.id_program == program.id,
            AcademicPeriod.code == code,
            AcademicPeriod.id != period.id,
        )
        .first()
    ):
        _conflict("Une période avec ce code existe déjà pour ce programme et cette année.")

    period.id_annee = annee.id
    period.id_program = program.id
    period.school_id = annee.school_id
    for key, value in payload.items():
        if key in {"id_annee", "id_program"}:
            continue
        setattr(period, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _conflict("Conflit d'unicité sur la période académique.")
    _audit(
        "PERIOD_UPDATED",
        "academic_period",
        period.id,
        details={"changed": list(payload.keys())},
    )
    return period


def deactivate_period(db: Session, period_id: uuid.UUID) -> AcademicPeriod:
    period = get_or_404_tenant(AcademicPeriod, period_id)
    period.is_active = False
    db.commit()
    _audit("PERIOD_DEACTIVATED", "academic_period", period.id, details={"code": period.code})
    return period


def serialize_period(period: AcademicPeriod, *, legacy: bool = False) -> dict:
    def _d(value):
        if isinstance(value, date):
            return value.isoformat()
        return str(value) if value is not None else None

    if legacy:
        return {
            "id": str(period.id),
            "id_annee": str(period.id_annee),
            "numero": period.sequence,
            "date_debut": _d(period.date_debut),
            "date_fin": _d(period.date_fin),
        }
    return {
        "id": str(period.id),
        "id_annee": str(period.id_annee),
        "id_program": str(period.id_program),
        "sequence": period.sequence,
        "code": period.code,
        "label": period.label,
        "period_type": period.period_type,
        "date_debut": _d(period.date_debut),
        "date_fin": _d(period.date_fin),
        "is_active": period.is_active,
        "created_at": period.created_at.isoformat() if period.created_at else None,
        "updated_at": period.updated_at.isoformat() if period.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Niveau / Classe — cohérence Program
# ---------------------------------------------------------------------------


def resolve_niveau_program_id(db: Session, data: dict, school_id: uuid.UUID) -> uuid.UUID:
    reject_client_school_id(data)
    raw_id = data.get("id_program") or data.get("program_id")
    if raw_id:
        program = get_or_404_tenant(Program, raw_id)
        return program.id
    return get_or_create_general_program(db, school_id).id


def resolve_classe_program_id(db: Session, data: dict) -> uuid.UUID:
    """Force program = niveau.program (refuse incohérence client)."""
    reject_client_school_id(data)
    niveau = get_or_404_tenant(NiveauEtude, data["id_niveau"])
    client_program = data.get("id_program") or data.get("program_id")
    if client_program is not None and str(client_program) != str(niveau.id_program):
        _bad_request("id_program doit correspondre au programme du niveau.")
    return niveau.id_program
