"""PR #12 Step 3 — API métier GradingRuleset (CRUD + workflow + resolve).

Consomme le moteur Step 2 (`resolve_grading_rules`) — ne recrée pas la priorité.
Ne calcule aucune note / moyenne / bulletin.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, noload, selectinload

from app.auth.jwt_handler import get_current_user
from app.models.etablissement import AnneeScolaire, Classe, NiveauEtude, Program
from app.models.grading import (
    AUDIT_GRADING_RULE_COMPONENT_CREATED,
    AUDIT_GRADING_RULE_COMPONENT_DELETED,
    AUDIT_GRADING_RULE_COMPONENT_UPDATED,
    AUDIT_GRADING_RULESET_ACTIVATED,
    AUDIT_GRADING_RULESET_ARCHIVED,
    AUDIT_GRADING_RULESET_CREATED,
    AUDIT_GRADING_RULESET_UPDATED,
    DEFAULT_SCALE_MAX,
    EVALUATION_CONTEXTS,
    GRADING_ROUNDING_MODES,
    GRADING_RULESET_STATUS_ACTIVE,
    GRADING_RULESET_STATUS_ARCHIVED,
    GRADING_RULESET_STATUS_DRAFT,
    GRADING_RULESET_STATUSES,
    WEIGHT_PERCENT_SCALE,
    EvaluationType,
    GradingRuleComponent,
    GradingRuleset,
)
from app.models.pedagogie import Matiere
from app.services.grading_rules import (
    GradingContextError,
    GradingRulesConflictError,
    GradingRulesInvalidError,
    GradingRulesNotFoundError,
    ResolutionContext,
    ResolvedGradingRules,
    resolve_grading_rules,
    validate_component_weights,
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
from app.utils.errors import abort_api

# Champs patchables sur un DRAFT uniquement
_PATCHABLE_RULESET = frozenset(
    {
        "code",
        "name",
        "description",
        "id_program",
        "id_niveau",
        "id_matiere",
        "id_annee",
        "scale_max",
        "rounding_mode",
        "rounding_precision",
    }
)
_PATCHABLE_COMPONENT = frozenset(
    {
        "code",
        "label",
        "id_evaluation_type",
        "evaluation_context",
        "weight",
        "sequence",
        "is_required",
    }
)


# ---------------------------------------------------------------------------
# Helpers
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


def _uuid_or_none(value: Any) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _pick_uuid(data: dict, *keys: str) -> uuid.UUID | None:
    for key in keys:
        if key in data and data[key] is not None:
            return _uuid_or_none(data[key])
    return None


def _parse_decimal(value: Any, *, field: str) -> Decimal:
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        abort_api(400, "INVALID_WEIGHT", f"{field} invalide.", details={"field": field})
    if not dec.is_finite():
        abort_api(400, "INVALID_WEIGHT", f"{field} invalide.", details={"field": field})
    return dec


def _validate_weight(value: Any) -> Decimal:
    weight = _parse_decimal(value, field="weight")
    if weight <= 0 or weight > WEIGHT_PERCENT_SCALE:
        abort_api(
            400,
            "INVALID_WEIGHT",
            f"Poids invalide : {weight} (attendu > 0 et ≤ {WEIGHT_PERCENT_SCALE}).",
            details={"weight": str(weight)},
        )
    # Aligné Numeric(5,2)
    if weight.as_tuple().exponent < -2:
        abort_api(
            400,
            "INVALID_WEIGHT",
            "Précision du poids limitée à 2 décimales.",
            details={"weight": str(weight)},
        )
    return weight.quantize(Decimal("0.01"))


def _reject_unsupported_scope_axes(data: dict) -> None:
    """V1 : class / period ne sont pas des axes de ruleset."""
    for key in ("class_id", "academic_period_id", "id_classe", "id_periode"):
        if data.get(key) is not None:
            abort_api(
                400,
                "INVALID_RULESET_SCOPE",
                "Les axes class_id / academic_period_id ne sont pas supportés sur un ruleset V1 "
                "(utilisables uniquement pour la résolution / validation de contexte).",
                details={"unsupported_field": key},
            )


def _reject_forced_lifecycle_fields(data: dict) -> None:
    if "status" in data and data["status"] is not None:
        abort_api(
            400,
            "INVALID_RULESET_STATUS",
            "Le statut ne peut pas être forcé via create/update — utiliser /activate ou /archive.",
        )
    if "version" in data and data["version"] is not None:
        abort_api(
            400,
            "INVALID_RULESET_STATUS",
            "La version est attribuée par le serveur.",
        )
    if "created_by" in data and data["created_by"] is not None:
        abort_api(400, "BAD_REQUEST", "created_by est déterminé par le serveur.")


def _require_draft(ruleset: GradingRuleset) -> None:
    if ruleset.status != GRADING_RULESET_STATUS_DRAFT:
        abort_api(
            409,
            "INVALID_RULESET_STATUS",
            f"Modification interdite : ruleset en statut « {ruleset.status} » (DRAFT requis).",
            details={"status": ruleset.status, "ruleset_id": str(ruleset.id)},
        )


def _next_version(db: Session, *, school_id: uuid.UUID, code: str) -> int:
    current = (
        db.query(func.max(GradingRuleset.version))
        .filter(GradingRuleset.school_id == school_id, GradingRuleset.code == code)
        .scalar()
    )
    return int(current or 0) + 1


def _validate_scope_entities(
    db: Session,
    *,
    school_id: uuid.UUID,
    id_annee: uuid.UUID,
    id_program: uuid.UUID | None,
    id_niveau: uuid.UUID | None,
    id_matiere: uuid.UUID | None,
) -> None:
    year = get_or_404_tenant(AnneeScolaire, id_annee)
    if year.school_id != school_id:
        abort_api(404, "RULESET_NOT_FOUND", "Année scolaire introuvable.")

    program: Program | None = None
    if id_program is not None:
        program = get_or_404_tenant(Program, id_program)
        if program.school_id != school_id:
            abort_api(404, "RULESET_NOT_FOUND", "Programme introuvable.")

    if id_niveau is not None:
        if id_program is None:
            abort_api(
                400,
                "INVALID_RULESET_SCOPE",
                "id_niveau nécessite id_program (contrainte modèle).",
            )
        level = get_or_404_tenant(NiveauEtude, id_niveau)
        if level.id_program != id_program:
            abort_api(
                400,
                "INVALID_RULESET_SCOPE",
                "Niveau incohérent avec le programme.",
                details={
                    "level_id": str(id_niveau),
                    "level_program_id": str(level.id_program),
                    "program_id": str(id_program),
                },
            )

    if id_matiere is not None:
        get_or_404_tenant(Matiere, id_matiere)


def _load_ruleset(db: Session, ruleset_id: uuid.UUID, *, with_components: bool = True) -> GradingRuleset:
    q = tenant_query(GradingRuleset).filter(GradingRuleset.id == ruleset_id)
    if with_components:
        q = q.options(selectinload(GradingRuleset.components))
    else:
        q = q.options(noload(GradingRuleset.components))
    ruleset = q.first()
    if ruleset is None:
        abort_api(404, "RULESET_NOT_FOUND", "Ruleset introuvable.")
    return ruleset


def _get_eval_type(db: Session, evaluation_type_id: uuid.UUID) -> EvaluationType:
    et = (
        tenant_query(EvaluationType)
        .filter(EvaluationType.id == evaluation_type_id)
        .first()
    )
    if et is None:
        abort_api(404, "INVALID_EVALUATION_TYPE", "Type d'évaluation introuvable.")
    if not et.is_active:
        abort_api(
            400,
            "INVALID_EVALUATION_TYPE",
            f"Type d'évaluation « {et.code} » inactif.",
            details={"evaluation_type_id": str(et.id), "code": et.code},
        )
    return et


def _serialize_component(comp: GradingRuleComponent, et: EvaluationType | None = None) -> dict:
    data = {
        "id": str(comp.id),
        "code": comp.code,
        "label": comp.label,
        "evaluation_type_id": str(comp.id_evaluation_type),
        "evaluation_context": comp.evaluation_context,
        "weight": str(Decimal(str(comp.weight))),
        "sequence": comp.sequence,
        "is_required": comp.is_required,
        "created_at": comp.created_at.isoformat() if comp.created_at else None,
        "updated_at": comp.updated_at.isoformat() if comp.updated_at else None,
    }
    if et is not None:
        data["evaluation_type"] = {
            "id": str(et.id),
            "code": et.code,
            "label": et.label,
            "is_system": et.is_system,
            "is_active": et.is_active,
        }
    return data


def _component_types_map(
    db: Session, components: list[GradingRuleComponent]
) -> dict[uuid.UUID, EvaluationType]:
    if not components:
        return {}
    ids = {c.id_evaluation_type for c in components}
    rows = (
        tenant_query(EvaluationType).filter(EvaluationType.id.in_(ids)).all()
    )
    return {r.id: r for r in rows}


def serialize_ruleset(
    db: Session,
    ruleset: GradingRuleset,
    *,
    with_components: bool = True,
) -> dict:
    data = {
        "id": str(ruleset.id),
        "code": ruleset.code,
        "name": ruleset.name,
        "description": ruleset.description,
        "status": ruleset.status,
        "version": ruleset.version,
        "academic_year_id": str(ruleset.id_annee),
        "program_id": str(ruleset.id_program) if ruleset.id_program else None,
        "level_id": str(ruleset.id_niveau) if ruleset.id_niveau else None,
        "subject_id": str(ruleset.id_matiere) if ruleset.id_matiere else None,
        # Axes V1 absents du modèle — exposés null pour compatibilité FE future
        "class_id": None,
        "academic_period_id": None,
        "scale_max": str(Decimal(str(ruleset.scale_max))),
        "rounding_mode": ruleset.rounding_mode,
        "rounding_precision": ruleset.rounding_precision,
        "created_by": str(ruleset.created_by) if ruleset.created_by else None,
        "activated_at": ruleset.activated_at.isoformat() if ruleset.activated_at else None,
        "archived_at": ruleset.archived_at.isoformat() if ruleset.archived_at else None,
        "created_at": ruleset.created_at.isoformat() if ruleset.created_at else None,
        "updated_at": ruleset.updated_at.isoformat() if ruleset.updated_at else None,
        "scope": {
            "academic_year_id": str(ruleset.id_annee),
            "program_id": str(ruleset.id_program) if ruleset.id_program else None,
            "level_id": str(ruleset.id_niveau) if ruleset.id_niveau else None,
            "subject_id": str(ruleset.id_matiere) if ruleset.id_matiere else None,
            "class_id": None,
            "academic_period_id": None,
        },
    }
    if with_components:
        comps = sorted(ruleset.components, key=lambda c: c.sequence)
        types = _component_types_map(db, comps)
        data["components"] = [
            _serialize_component(c, types.get(c.id_evaluation_type)) for c in comps
        ]
        data["components_count"] = len(comps)
    else:
        data["components_count"] = (
            db.query(func.count(GradingRuleComponent.id))
            .filter(GradingRuleComponent.ruleset_id == ruleset.id)
            .scalar()
            or 0
        )
    return data


def serialize_resolve_result(result: ResolvedGradingRules, *, diagnostic: bool = False) -> dict:
    payload = {
        "ruleset": {
            "id": str(result.ruleset_id),
            "code": result.ruleset_code,
            "version": result.ruleset_version,
            "status": GRADING_RULESET_STATUS_ACTIVE,
        },
        "scope": {
            "description": result.scope_description,
            "level": result.scope_level,
            "specificity": result.specificity,
        },
        "scale": {"max": str(result.scale_max)},
        "rounding": {
            "mode": result.rounding_mode,
            "precision": result.rounding_precision,
        },
        "components": [
            {
                "id": str(c.id),
                "code": c.code,
                "label": c.label,
                "evaluation_type_id": str(c.evaluation_type_id),
                "evaluation_type_code": c.evaluation_type_code,
                "evaluation_context": c.evaluation_context,
                "weight": str(c.weight),
                "sequence": c.sequence,
                "is_required": c.is_required,
            }
            for c in result.components
        ],
    }
    if diagnostic and result.trace is not None:
        payload["diagnostic"] = {
            "selected": (
                {
                    "ruleset_id": str(result.trace.selected.ruleset_id),
                    "code": result.trace.selected.code,
                    "version": result.trace.selected.version,
                    "specificity": result.trace.selected.specificity,
                    "scope_description": result.trace.selected.scope_description,
                }
                if result.trace.selected
                else None
            ),
            "candidates": [
                {
                    "ruleset_id": str(c.ruleset_id),
                    "code": c.code,
                    "version": c.version,
                    "status": c.status,
                    "specificity": c.specificity,
                    "scope_description": c.scope_description,
                }
                for c in result.trace.candidates
            ],
            "notes": list(result.trace.notes),
        }
    return payload


# ---------------------------------------------------------------------------
# Evaluation types (lecture catalogue)
# ---------------------------------------------------------------------------


def list_evaluation_types(db: Session, *, active_only: bool = True) -> list[dict]:
    q = tenant_query(EvaluationType).order_by(EvaluationType.code.asc())
    if active_only:
        q = q.filter(EvaluationType.is_active.is_(True))
    return [
        {
            "id": str(et.id),
            "code": et.code,
            "label": et.label,
            "is_system": et.is_system,
            "is_active": et.is_active,
        }
        for et in q.all()
    ]


# ---------------------------------------------------------------------------
# List / get
# ---------------------------------------------------------------------------


def list_rulesets(
    db: Session,
    *,
    academic_year_id: uuid.UUID | None = None,
    program_id: uuid.UUID | None = None,
    level_id: uuid.UUID | None = None,
    subject_id: uuid.UUID | None = None,
    status: str | None = None,
    class_id: uuid.UUID | None = None,
    academic_period_id: uuid.UUID | None = None,
    page: int = 1,
    per_page: int = 25,
) -> tuple[list[dict], int, int]:
    # class/period : validation tenant uniquement (pas d'axe de filtre V1)
    if class_id is not None:
        get_or_404_tenant(Classe, class_id)
    if academic_period_id is not None:
        from app.models.etablissement import AcademicPeriod

        get_or_404_tenant(AcademicPeriod, academic_period_id)

    q = tenant_query(GradingRuleset).options(noload(GradingRuleset.components))
    if academic_year_id is not None:
        get_or_404_tenant(AnneeScolaire, academic_year_id)
        q = q.filter(GradingRuleset.id_annee == academic_year_id)
    if program_id is not None:
        get_or_404_tenant(Program, program_id)
        q = q.filter(GradingRuleset.id_program == program_id)
    if level_id is not None:
        get_or_404_tenant(NiveauEtude, level_id)
        q = q.filter(GradingRuleset.id_niveau == level_id)
    if subject_id is not None:
        get_or_404_tenant(Matiere, subject_id)
        q = q.filter(GradingRuleset.id_matiere == subject_id)
    if status is not None:
        if status not in GRADING_RULESET_STATUSES:
            abort_api(
                400,
                "INVALID_RULESET_STATUS",
                f"Statut invalide. Valeurs : {', '.join(GRADING_RULESET_STATUSES)}.",
            )
        q = q.filter(GradingRuleset.status == status)

    q = q.order_by(
        GradingRuleset.code.asc(),
        GradingRuleset.version.desc(),
        GradingRuleset.created_at.desc(),
    )
    total = q.count()
    pages = max((total + per_page - 1) // per_page, 1) if total else 0
    rows = q.offset((page - 1) * per_page).limit(per_page).all()
    return [serialize_ruleset(db, r, with_components=False) for r in rows], total, pages


def get_ruleset(db: Session, ruleset_id: uuid.UUID) -> dict:
    ruleset = _load_ruleset(db, ruleset_id, with_components=True)
    return serialize_ruleset(db, ruleset, with_components=True)


# ---------------------------------------------------------------------------
# Create / update
# ---------------------------------------------------------------------------


def _build_component_from_payload(
    db: Session,
    *,
    school_id: uuid.UUID,
    ruleset_id: uuid.UUID,
    raw: dict,
) -> GradingRuleComponent:
    reject_client_school_id(raw)
    code = (raw.get("code") or "").strip()
    label = (raw.get("label") or "").strip()
    if not code or not label:
        abort_api(400, "INVALID_COMPONENT", "code et label sont obligatoires.")
    et_id = _uuid_or_none(raw.get("evaluation_type_id") or raw.get("id_evaluation_type"))
    if et_id is None:
        abort_api(400, "INVALID_EVALUATION_TYPE", "evaluation_type_id est obligatoire.")
    et = _get_eval_type(db, et_id)
    weight = _validate_weight(raw.get("weight"))
    try:
        sequence = int(raw.get("sequence"))
    except (TypeError, ValueError):
        abort_api(400, "INVALID_COMPONENT", "sequence invalide.")
    if sequence < 1:
        abort_api(400, "INVALID_COMPONENT", "sequence doit être ≥ 1.")
    ctx = (raw.get("evaluation_context") or "normal").strip()
    if ctx not in EVALUATION_CONTEXTS:
        abort_api(
            400,
            "INVALID_COMPONENT",
            f"evaluation_context invalide. Valeurs : {', '.join(EVALUATION_CONTEXTS)}.",
        )
    return GradingRuleComponent(
        id=uuid.uuid4(),
        school_id=school_id,
        ruleset_id=ruleset_id,
        code=code,
        label=label,
        id_evaluation_type=et.id,
        evaluation_context=ctx,
        weight=weight,
        sequence=sequence,
        is_required=bool(raw.get("is_required", True)),
    )


def create_ruleset(db: Session, data: dict) -> dict:
    reject_client_school_id(data)
    _reject_forced_lifecycle_fields(data)
    _reject_unsupported_scope_axes(data)

    code = (data.get("code") or "").strip().upper()
    name = (data.get("name") or "").strip()
    if not code or not name:
        abort_api(400, "BAD_REQUEST", "code et name sont obligatoires.")

    id_annee = _pick_uuid(data, "academic_year_id", "id_annee")
    if id_annee is None:
        abort_api(400, "INVALID_RULESET_SCOPE", "academic_year_id est obligatoire.")

    id_program = _pick_uuid(data, "program_id", "id_program")
    id_niveau = _pick_uuid(data, "level_id", "id_niveau")
    id_matiere = _pick_uuid(data, "subject_id", "id_matiere")

    school_id = get_current_school_id()
    _validate_scope_entities(
        db,
        school_id=school_id,
        id_annee=id_annee,
        id_program=id_program,
        id_niveau=id_niveau,
        id_matiere=id_matiere,
    )

    scale_max = _parse_decimal(data.get("scale_max", DEFAULT_SCALE_MAX), field="scale_max")
    if scale_max <= 0:
        abort_api(400, "BAD_REQUEST", "scale_max doit être > 0.")
    rounding_mode = (data.get("rounding_mode") or "half_up").strip()
    if rounding_mode not in GRADING_ROUNDING_MODES:
        abort_api(400, "BAD_REQUEST", "rounding_mode invalide.")
    rounding_precision = int(data.get("rounding_precision", 2))
    if rounding_precision < 0:
        abort_api(400, "BAD_REQUEST", "rounding_precision invalide.")

    user = get_current_user()
    version = _next_version(db, school_id=school_id, code=code)
    ruleset = apply_tenant_school(
        GradingRuleset(
            id=uuid.uuid4(),
            code=code,
            name=name,
            description=data.get("description"),
            status=GRADING_RULESET_STATUS_DRAFT,
            version=version,
            id_annee=id_annee,
            id_program=id_program,
            id_niveau=id_niveau,
            id_matiere=id_matiere,
            scale_max=scale_max.quantize(Decimal("0.01")),
            rounding_mode=rounding_mode,
            rounding_precision=rounding_precision,
            created_by=user.id if user else None,
        )
    )
    db.add(ruleset)
    db.flush()

    raw_components = data.get("components")
    if raw_components:
        if not isinstance(raw_components, list):
            abort_api(400, "INVALID_COMPONENT", "components doit être une liste.")
        for raw in raw_components:
            if not isinstance(raw, dict):
                abort_api(400, "INVALID_COMPONENT", "Chaque composant doit être un objet.")
            db.add(
                _build_component_from_payload(
                    db, school_id=school_id, ruleset_id=ruleset.id, raw=raw
                )
            )
        db.flush()
        # DRAFT : somme non obligatoire ; on valide seulement si composants présents
        # qu'ils sont individuellement OK (déjà fait). Somme 100 exigée à l'activation.

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        abort_api(
            409,
            "CONFLICT",
            "Conflit d'unicité (code/version ou composant).",
            details={"code": code, "version": version},
        )

    db.refresh(ruleset)
    _audit(
        AUDIT_GRADING_RULESET_CREATED,
        "grading_ruleset",
        ruleset.id,
        details={
            "code": ruleset.code,
            "version": ruleset.version,
            "status": ruleset.status,
            "components_count": len(raw_components or []),
        },
    )
    return serialize_ruleset(db, _load_ruleset(db, ruleset.id), with_components=True)


def update_ruleset(db: Session, ruleset_id: uuid.UUID, data: dict) -> dict:
    reject_client_school_id(data)
    _reject_forced_lifecycle_fields(data)
    _reject_unsupported_scope_axes(data)

    ruleset = _load_ruleset(db, ruleset_id, with_components=True)
    _require_draft(ruleset)

    # Normaliser alias → colonnes modèle
    normalized: dict[str, Any] = {}
    if "code" in data and data["code"] is not None:
        normalized["code"] = str(data["code"]).strip().upper()
    if "name" in data and data["name"] is not None:
        normalized["name"] = str(data["name"]).strip()
    if "description" in data:
        normalized["description"] = data["description"]
    if any(k in data for k in ("program_id", "id_program")):
        normalized["id_program"] = _pick_uuid(data, "program_id", "id_program")
    if any(k in data for k in ("level_id", "id_niveau")):
        normalized["id_niveau"] = _pick_uuid(data, "level_id", "id_niveau")
    if any(k in data for k in ("subject_id", "id_matiere")):
        normalized["id_matiere"] = _pick_uuid(data, "subject_id", "id_matiere")
    if any(k in data for k in ("academic_year_id", "id_annee")):
        year = _pick_uuid(data, "academic_year_id", "id_annee")
        if year is None:
            abort_api(400, "INVALID_RULESET_SCOPE", "academic_year_id ne peut pas être null.")
        normalized["id_annee"] = year
    if "scale_max" in data and data["scale_max"] is not None:
        sm = _parse_decimal(data["scale_max"], field="scale_max")
        if sm <= 0:
            abort_api(400, "BAD_REQUEST", "scale_max doit être > 0.")
        normalized["scale_max"] = sm.quantize(Decimal("0.01"))
    if "rounding_mode" in data and data["rounding_mode"] is not None:
        rm = str(data["rounding_mode"]).strip()
        if rm not in GRADING_ROUNDING_MODES:
            abort_api(400, "BAD_REQUEST", "rounding_mode invalide.")
        normalized["rounding_mode"] = rm
    if "rounding_precision" in data and data["rounding_precision"] is not None:
        normalized["rounding_precision"] = int(data["rounding_precision"])

    payload = {k: v for k, v in normalized.items() if k in _PATCHABLE_RULESET}
    if not payload:
        return serialize_ruleset(db, ruleset, with_components=True)

    # Code change → version lineage : code unique par version ; changing code on draft ok
    # if another draft same code+version — conflict handled by DB

    id_annee = payload.get("id_annee", ruleset.id_annee)
    # `in` requis : None explicite = wildcard (≠ clé absente). noqa: SIM401
    id_program = payload["id_program"] if "id_program" in payload else ruleset.id_program  # noqa: SIM401
    id_niveau = payload["id_niveau"] if "id_niveau" in payload else ruleset.id_niveau  # noqa: SIM401
    id_matiere = payload["id_matiere"] if "id_matiere" in payload else ruleset.id_matiere  # noqa: SIM401

    # Si on change le code, recalculer version pour le nouveau code
    if "code" in payload and payload["code"] != ruleset.code:
        payload["version"] = _next_version(db, school_id=ruleset.school_id, code=payload["code"])

    _validate_scope_entities(
        db,
        school_id=ruleset.school_id,
        id_annee=id_annee,
        id_program=id_program,
        id_niveau=id_niveau,
        id_matiere=id_matiere,
    )

    before = {
        "code": ruleset.code,
        "name": ruleset.name,
        "id_program": str(ruleset.id_program) if ruleset.id_program else None,
        "id_niveau": str(ruleset.id_niveau) if ruleset.id_niveau else None,
        "id_matiere": str(ruleset.id_matiere) if ruleset.id_matiere else None,
    }
    for key, value in payload.items():
        setattr(ruleset, key, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        abort_api(409, "CONFLICT", "Conflit d'unicité lors de la mise à jour du ruleset.")

    _audit(
        AUDIT_GRADING_RULESET_UPDATED,
        "grading_ruleset",
        ruleset.id,
        details={"changed": list(payload.keys()), "before": before},
    )
    return serialize_ruleset(db, _load_ruleset(db, ruleset.id), with_components=True)


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------


def add_component(db: Session, ruleset_id: uuid.UUID, data: dict) -> dict:
    reject_client_school_id(data)
    ruleset = _load_ruleset(db, ruleset_id, with_components=True)
    _require_draft(ruleset)
    comp = _build_component_from_payload(
        db, school_id=ruleset.school_id, ruleset_id=ruleset.id, raw=data
    )
    db.add(comp)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        abort_api(
            409,
            "CONFLICT",
            "Conflit d'unicité composant (code ou sequence déjà utilisé).",
        )
    _audit(
        AUDIT_GRADING_RULE_COMPONENT_CREATED,
        "grading_rule_component",
        comp.id,
        details={"ruleset_id": str(ruleset.id), "code": comp.code, "weight": str(comp.weight)},
    )
    et = _get_eval_type(db, comp.id_evaluation_type)
    return _serialize_component(comp, et)


def update_component(
    db: Session, ruleset_id: uuid.UUID, component_id: uuid.UUID, data: dict
) -> dict:
    reject_client_school_id(data)
    ruleset = _load_ruleset(db, ruleset_id, with_components=True)
    _require_draft(ruleset)
    comp = next((c for c in ruleset.components if c.id == component_id), None)
    if comp is None:
        abort_api(404, "INVALID_COMPONENT", "Composant introuvable.")

    payload: dict[str, Any] = {}
    if "code" in data and data["code"] is not None:
        payload["code"] = str(data["code"]).strip()
    if "label" in data and data["label"] is not None:
        payload["label"] = str(data["label"]).strip()
    if "evaluation_type_id" in data or "id_evaluation_type" in data:
        et_id = _pick_uuid(data, "evaluation_type_id", "id_evaluation_type")
        if et_id is None:
            abort_api(400, "INVALID_EVALUATION_TYPE", "evaluation_type_id invalide.")
        et = _get_eval_type(db, et_id)
        payload["id_evaluation_type"] = et.id
    if "evaluation_context" in data and data["evaluation_context"] is not None:
        ctx = str(data["evaluation_context"]).strip()
        if ctx not in EVALUATION_CONTEXTS:
            abort_api(400, "INVALID_COMPONENT", "evaluation_context invalide.")
        payload["evaluation_context"] = ctx
    if "weight" in data and data["weight"] is not None:
        payload["weight"] = _validate_weight(data["weight"])
    if "sequence" in data and data["sequence"] is not None:
        payload["sequence"] = int(data["sequence"])
    if "is_required" in data and data["is_required"] is not None:
        payload["is_required"] = bool(data["is_required"])

    payload = {k: v for k, v in payload.items() if k in _PATCHABLE_COMPONENT}
    if not payload:
        et = _get_eval_type(db, comp.id_evaluation_type)
        return _serialize_component(comp, et)

    before = {"code": comp.code, "weight": str(comp.weight), "sequence": comp.sequence}
    for key, value in payload.items():
        setattr(comp, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        abort_api(409, "CONFLICT", "Conflit d'unicité composant.")
    _audit(
        AUDIT_GRADING_RULE_COMPONENT_UPDATED,
        "grading_rule_component",
        comp.id,
        details={"ruleset_id": str(ruleset.id), "changed": list(payload.keys()), "before": before},
    )
    et = _get_eval_type(db, comp.id_evaluation_type)
    return _serialize_component(comp, et)


def delete_component(db: Session, ruleset_id: uuid.UUID, component_id: uuid.UUID) -> dict:
    ruleset = _load_ruleset(db, ruleset_id, with_components=True)
    _require_draft(ruleset)
    comp = next((c for c in ruleset.components if c.id == component_id), None)
    if comp is None:
        abort_api(404, "INVALID_COMPONENT", "Composant introuvable.")
    code = comp.code
    db.delete(comp)
    db.commit()
    _audit(
        AUDIT_GRADING_RULE_COMPONENT_DELETED,
        "grading_rule_component",
        component_id,
        details={"ruleset_id": str(ruleset.id), "code": code},
    )
    return {"id": str(component_id), "deleted": True}


# ---------------------------------------------------------------------------
# Activate / archive
# ---------------------------------------------------------------------------


def _same_scope_filter(ruleset: GradingRuleset):
    return (
        GradingRuleset.school_id == ruleset.school_id,
        GradingRuleset.id_annee == ruleset.id_annee,
        GradingRuleset.id_program.is_(None)
        if ruleset.id_program is None
        else GradingRuleset.id_program == ruleset.id_program,
        GradingRuleset.id_niveau.is_(None)
        if ruleset.id_niveau is None
        else GradingRuleset.id_niveau == ruleset.id_niveau,
        GradingRuleset.id_matiere.is_(None)
        if ruleset.id_matiere is None
        else GradingRuleset.id_matiere == ruleset.id_matiere,
        GradingRuleset.status == GRADING_RULESET_STATUS_ACTIVE,
        GradingRuleset.id != ruleset.id,
    )


def activate_ruleset(db: Session, ruleset_id: uuid.UUID) -> dict:
    ruleset = (
        tenant_query(GradingRuleset)
        .options(selectinload(GradingRuleset.components))
        .filter(GradingRuleset.id == ruleset_id)
        .with_for_update()
        .first()
    )
    if ruleset is None:
        abort_api(404, "RULESET_NOT_FOUND", "Ruleset introuvable.")

    if ruleset.status == GRADING_RULESET_STATUS_ACTIVE:
        abort_api(
            409,
            "RULESET_ALREADY_ACTIVE",
            "Ruleset déjà ACTIVE.",
            details={"ruleset_id": str(ruleset.id)},
        )
    if ruleset.status == GRADING_RULESET_STATUS_ARCHIVED:
        abort_api(
            409,
            "INVALID_RULESET_STATUS",
            "Impossible d'activer un ruleset ARCHIVED.",
            details={"status": ruleset.status},
        )
    if ruleset.status != GRADING_RULESET_STATUS_DRAFT:
        abort_api(409, "INVALID_RULESET_STATUS", f"Transition interdite depuis « {ruleset.status} ».")

    _validate_scope_entities(
        db,
        school_id=ruleset.school_id,
        id_annee=ruleset.id_annee,
        id_program=ruleset.id_program,
        id_niveau=ruleset.id_niveau,
        id_matiere=ruleset.id_matiere,
    )

    components = sorted(ruleset.components, key=lambda c: c.sequence)
    if not components:
        abort_api(
            400,
            "INVALID_COMPONENT",
            "Activation impossible : aucun composant.",
            details={"ruleset_id": str(ruleset.id)},
        )
    try:
        validate_component_weights(components)
    except GradingRulesInvalidError as exc:
        abort_api(
            400,
            "INVALID_WEIGHT_SUM",
            exc.message,
            details=exc.details,
        )

    # Types toujours actifs
    for c in components:
        et = (
            tenant_query(EvaluationType)
            .filter(EvaluationType.id == c.id_evaluation_type)
            .first()
        )
        if et is None or not et.is_active:
            abort_api(
                400,
                "INVALID_EVALUATION_TYPE",
                "Composant référence un type d'évaluation invalide ou inactif.",
                details={"component_id": str(c.id)},
            )

    # Concurrence : verrouiller les ACTIVE même scope
    conflicts = (
        tenant_query(GradingRuleset)
        .filter(*_same_scope_filter(ruleset))
        .with_for_update()
        .all()
    )
    # Même code (nouvelle version) → archiver automatiquement les ACTIVE du même code
    archived_ids: list[str] = []
    remaining_conflicts: list[GradingRuleset] = []
    now = datetime.now(UTC)
    for other in conflicts:
        if other.code == ruleset.code:
            other.status = GRADING_RULESET_STATUS_ARCHIVED
            other.archived_at = now
            archived_ids.append(str(other.id))
        else:
            remaining_conflicts.append(other)

    if remaining_conflicts:
        abort_api(
            409,
            "RULESET_CONFLICT",
            "Un autre ruleset ACTIVE existe déjà avec le même scope.",
            details={
                "conflicting_ruleset_ids": [str(r.id) for r in remaining_conflicts],
                "conflicting_codes": [r.code for r in remaining_conflicts],
            },
        )

    ruleset.status = GRADING_RULESET_STATUS_ACTIVE
    ruleset.activated_at = now
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        abort_api(409, "CONFLICT", "Conflit lors de l'activation.")

    _audit(
        AUDIT_GRADING_RULESET_ACTIVATED,
        "grading_ruleset",
        ruleset.id,
        details={
            "code": ruleset.code,
            "version": ruleset.version,
            "auto_archived": archived_ids,
        },
    )
    return serialize_ruleset(db, _load_ruleset(db, ruleset.id), with_components=True)


def archive_ruleset(db: Session, ruleset_id: uuid.UUID) -> dict:
    ruleset = (
        tenant_query(GradingRuleset)
        .filter(GradingRuleset.id == ruleset_id)
        .with_for_update()
        .first()
    )
    if ruleset is None:
        abort_api(404, "RULESET_NOT_FOUND", "Ruleset introuvable.")

    if ruleset.status == GRADING_RULESET_STATUS_ARCHIVED:
        abort_api(
            409,
            "RULESET_ALREADY_ARCHIVED",
            "Ruleset déjà ARCHIVED.",
            details={"ruleset_id": str(ruleset.id)},
        )
    # DRAFT → ARCHIVED et ACTIVE → ARCHIVED autorisés
    if ruleset.status not in (
        GRADING_RULESET_STATUS_DRAFT,
        GRADING_RULESET_STATUS_ACTIVE,
    ):
        abort_api(409, "INVALID_RULESET_STATUS", f"Transition interdite depuis « {ruleset.status} ».")

    before = ruleset.status
    ruleset.status = GRADING_RULESET_STATUS_ARCHIVED
    ruleset.archived_at = datetime.now(UTC)
    db.commit()
    _audit(
        AUDIT_GRADING_RULESET_ARCHIVED,
        "grading_ruleset",
        ruleset.id,
        details={"code": ruleset.code, "version": ruleset.version, "from_status": before},
    )
    return serialize_ruleset(db, _load_ruleset(db, ruleset.id), with_components=True)


# ---------------------------------------------------------------------------
# Resolve (consomme Step 2)
# ---------------------------------------------------------------------------


def resolve_via_api(db: Session, data: dict) -> dict:
    reject_client_school_id(data)
    school_id = get_current_school_id()

    id_annee = _pick_uuid(data, "academic_year_id", "id_annee")
    id_program = _pick_uuid(data, "program_id", "id_program")
    if id_annee is None or id_program is None:
        abort_api(
            400,
            "INVALID_ACADEMIC_CONTEXT",
            "academic_year_id et program_id sont obligatoires pour la résolution.",
        )

    ctx = ResolutionContext(
        school_id=school_id,
        academic_year_id=id_annee,
        program_id=id_program,
        level_id=_pick_uuid(data, "level_id", "id_niveau"),
        class_id=_uuid_or_none(data.get("class_id")),
        subject_id=_pick_uuid(data, "subject_id", "id_matiere"),
        academic_period_id=_uuid_or_none(data.get("academic_period_id")),
    )
    diagnostic = bool(data.get("diagnostic", False))

    try:
        result = resolve_grading_rules(db, ctx)
    except GradingContextError as exc:
        abort_api(400, "INVALID_ACADEMIC_CONTEXT", exc.message, details=exc.details)
    except GradingRulesNotFoundError as exc:
        abort_api(404, "NO_RULESET", exc.message, details=exc.details)
    except GradingRulesConflictError as exc:
        abort_api(409, "RULESET_CONFLICT", exc.message, details=exc.details)
    except GradingRulesInvalidError as exc:
        abort_api(400, "INVALID_WEIGHT_SUM", exc.message, details=exc.details)

    return serialize_resolve_result(result, diagnostic=diagnostic)
