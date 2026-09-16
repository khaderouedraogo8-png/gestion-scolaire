"""Routes API — Grading Rulesets (PR #12 Step 3)."""
from __future__ import annotations

import uuid

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.permissions import require_role
from app.extensions import get_db
from app.schemas.grading import (
    GradingComponentCreateSchema,
    GradingComponentUpdateSchema,
    GradingResolveSchema,
    GradingRulesetCreateSchema,
    GradingRulesetUpdateSchema,
)
from app.services import grading_rulesets as svc
from app.services.tenant import reject_client_school_id
from app.utils.pagination import pagination_payload, parse_pagination

blp = Blueprint(
    "grading_rulesets",
    __name__,
    description="Moteur de règles de notation — administration et résolution",
)

_READ_ROLES = ("administrateur", "directeur", "secretariat", "enseignant", "agent_comptable")
_WRITE_ROLES = ("administrateur", "directeur")


def _parse_uuid_arg(*names: str) -> uuid.UUID | None:
    for name in names:
        raw = request.args.get(name)
        if raw:
            return uuid.UUID(raw)
    return None


@blp.route("/evaluation-types")
class EvaluationTypesResource(MethodView):
    @jwt_required()
    @require_role(*_READ_ROLES)
    def get(self):
        db = get_db()
        active_only = request.args.get("active_only", "true").lower() not in ("0", "false", "no")
        return jsonify({"items": svc.list_evaluation_types(db, active_only=active_only)})

    @jwt_required()
    @require_role(*_WRITE_ROLES)
    def post(self):
        db = get_db()
        body = request.get_json(silent=True) or {}
        reject_client_school_id(body)
        return jsonify(
            svc.create_evaluation_type(
                db, code=body.get("code", ""), label=body.get("label", "")
            )
        ), 201


@blp.route("/evaluation-types/<uuid:type_id>/activate")
class EvaluationTypeActivate(MethodView):
    @jwt_required()
    @require_role(*_WRITE_ROLES)
    def post(self, type_id):
        db = get_db()
        return jsonify(svc.set_evaluation_type_active(db, type_id, is_active=True))


@blp.route("/evaluation-types/<uuid:type_id>/deactivate")
class EvaluationTypeDeactivate(MethodView):
    @jwt_required()
    @require_role(*_WRITE_ROLES)
    def post(self, type_id):
        db = get_db()
        return jsonify(svc.set_evaluation_type_active(db, type_id, is_active=False))


@blp.route("/grading-rulesets/resolve")
class GradingRulesetsResolve(MethodView):
    @jwt_required()
    @require_role(*_READ_ROLES)
    @blp.arguments(GradingResolveSchema)
    def post(self, data):
        db = get_db()
        reject_client_school_id(request.get_json(silent=True) or {})
        return jsonify(svc.resolve_via_api(db, data))


@blp.route("/grading-rulesets")
class GradingRulesetsResource(MethodView):
    @jwt_required()
    @require_role(*_READ_ROLES)
    def get(self):
        db = get_db()
        page, per_page = parse_pagination()
        status = request.args.get("status")
        items, total, pages = svc.list_rulesets(
            db,
            academic_year_id=_parse_uuid_arg("academic_year_id", "id_annee"),
            program_id=_parse_uuid_arg("program_id", "id_program"),
            level_id=_parse_uuid_arg("level_id", "id_niveau"),
            subject_id=_parse_uuid_arg("subject_id", "id_matiere"),
            class_id=_parse_uuid_arg("class_id"),
            academic_period_id=_parse_uuid_arg("academic_period_id"),
            status=status,
            page=page,
            per_page=per_page,
        )
        return jsonify(
            pagination_payload(items, page=page, per_page=per_page, total=total, pages=pages)
        )

    @jwt_required()
    @require_role(*_WRITE_ROLES)
    @blp.arguments(GradingRulesetCreateSchema)
    def post(self, data):
        db = get_db()
        reject_client_school_id(request.get_json(silent=True) or {})
        return jsonify(svc.create_ruleset(db, data)), 201


@blp.route("/grading-rulesets/<uuid:ruleset_id>")
class GradingRulesetDetail(MethodView):
    @jwt_required()
    @require_role(*_READ_ROLES)
    def get(self, ruleset_id):
        db = get_db()
        return jsonify(svc.get_ruleset(db, ruleset_id))

    @jwt_required()
    @require_role(*_WRITE_ROLES)
    @blp.arguments(GradingRulesetUpdateSchema)
    def patch(self, data, ruleset_id):
        db = get_db()
        reject_client_school_id(request.get_json(silent=True) or {})
        return jsonify(svc.update_ruleset(db, ruleset_id, data))


@blp.route("/grading-rulesets/<uuid:ruleset_id>/activate")
class GradingRulesetActivate(MethodView):
    @jwt_required()
    @require_role(*_WRITE_ROLES)
    def post(self, ruleset_id):
        db = get_db()
        return jsonify(svc.activate_ruleset(db, ruleset_id))


@blp.route("/grading-rulesets/<uuid:ruleset_id>/archive")
class GradingRulesetArchive(MethodView):
    @jwt_required()
    @require_role(*_WRITE_ROLES)
    def post(self, ruleset_id):
        db = get_db()
        return jsonify(svc.archive_ruleset(db, ruleset_id))


@blp.route("/grading-rulesets/<uuid:ruleset_id>/components")
class GradingRulesetComponents(MethodView):
    @jwt_required()
    @require_role(*_WRITE_ROLES)
    @blp.arguments(GradingComponentCreateSchema)
    def post(self, data, ruleset_id):
        db = get_db()
        reject_client_school_id(request.get_json(silent=True) or {})
        return jsonify(svc.add_component(db, ruleset_id, data)), 201


@blp.route("/grading-rulesets/<uuid:ruleset_id>/components/<uuid:component_id>")
class GradingRulesetComponentDetail(MethodView):
    @jwt_required()
    @require_role(*_WRITE_ROLES)
    @blp.arguments(GradingComponentUpdateSchema)
    def patch(self, data, ruleset_id, component_id):
        db = get_db()
        reject_client_school_id(request.get_json(silent=True) or {})
        return jsonify(svc.update_component(db, ruleset_id, component_id, data))

    @jwt_required()
    @require_role(*_WRITE_ROLES)
    def delete(self, ruleset_id, component_id):
        db = get_db()
        return jsonify(svc.delete_component(db, ruleset_id, component_id))
