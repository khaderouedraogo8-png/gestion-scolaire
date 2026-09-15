"""Schémas Marshmallow — Grading Rulesets API (PR #12 Step 3)."""
from __future__ import annotations

from marshmallow import INCLUDE, Schema, fields, validate

from app.models.grading import (
    EVALUATION_CONTEXTS,
    GRADING_ROUNDING_MODES,
    GRADING_RULESET_STATUSES,
)

# Alias acceptés : noms modèle (id_*) et noms API (academic_year_id, …)


class GradingRulesetCreateSchema(Schema):
    class Meta:
        unknown = INCLUDE

    code = fields.String(required=True, validate=validate.Length(min=1, max=40))
    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    description = fields.String(allow_none=True)
    academic_year_id = fields.UUID(load_default=None)
    id_annee = fields.UUID(load_default=None)
    program_id = fields.UUID(allow_none=True, load_default=None)
    id_program = fields.UUID(allow_none=True, load_default=None)
    level_id = fields.UUID(allow_none=True, load_default=None)
    id_niveau = fields.UUID(allow_none=True, load_default=None)
    subject_id = fields.UUID(allow_none=True, load_default=None)
    id_matiere = fields.UUID(allow_none=True, load_default=None)
    # V1 : non stockés sur grading_ruleset — rejetés au service si fournis
    class_id = fields.UUID(allow_none=True, load_default=None)
    academic_period_id = fields.UUID(allow_none=True, load_default=None)
    scale_max = fields.Decimal(as_string=True, places=2, load_default="20.00")
    rounding_mode = fields.String(
        load_default="half_up", validate=validate.OneOf(list(GRADING_ROUNDING_MODES))
    )
    rounding_precision = fields.Integer(load_default=2, validate=validate.Range(min=0, max=6))
    components = fields.List(fields.Dict(), load_default=None)
    # Anti-spoof — capturés puis rejetés
    school_id = fields.Raw(load_only=True, allow_none=True)
    status = fields.Raw(load_only=True, allow_none=True)
    version = fields.Raw(load_only=True, allow_none=True)
    created_by = fields.Raw(load_only=True, allow_none=True)


class GradingRulesetUpdateSchema(Schema):
    class Meta:
        unknown = INCLUDE

    code = fields.String(validate=validate.Length(min=1, max=40))
    name = fields.String(validate=validate.Length(min=1, max=150))
    description = fields.String(allow_none=True)
    program_id = fields.UUID(allow_none=True)
    id_program = fields.UUID(allow_none=True)
    level_id = fields.UUID(allow_none=True)
    id_niveau = fields.UUID(allow_none=True)
    subject_id = fields.UUID(allow_none=True)
    id_matiere = fields.UUID(allow_none=True)
    class_id = fields.UUID(allow_none=True)
    academic_period_id = fields.UUID(allow_none=True)
    scale_max = fields.Decimal(as_string=True, places=2)
    rounding_mode = fields.String(validate=validate.OneOf(list(GRADING_ROUNDING_MODES)))
    rounding_precision = fields.Integer(validate=validate.Range(min=0, max=6))
    school_id = fields.Raw(load_only=True, allow_none=True)
    status = fields.Raw(load_only=True, allow_none=True)
    version = fields.Raw(load_only=True, allow_none=True)
    academic_year_id = fields.UUID(allow_none=True)
    id_annee = fields.UUID(allow_none=True)


class GradingComponentCreateSchema(Schema):
    class Meta:
        unknown = INCLUDE

    code = fields.String(required=True, validate=validate.Length(min=1, max=40))
    label = fields.String(required=True, validate=validate.Length(min=1, max=100))
    evaluation_type_id = fields.UUID(required=True)
    evaluation_context = fields.String(
        load_default="normal", validate=validate.OneOf(list(EVALUATION_CONTEXTS))
    )
    weight = fields.Decimal(required=True, as_string=True, places=2)
    sequence = fields.Integer(required=True, validate=validate.Range(min=1, max=32767))
    is_required = fields.Boolean(load_default=True)
    school_id = fields.Raw(load_only=True, allow_none=True)


class GradingComponentUpdateSchema(Schema):
    class Meta:
        unknown = INCLUDE

    code = fields.String(validate=validate.Length(min=1, max=40))
    label = fields.String(validate=validate.Length(min=1, max=100))
    evaluation_type_id = fields.UUID()
    evaluation_context = fields.String(validate=validate.OneOf(list(EVALUATION_CONTEXTS)))
    weight = fields.Decimal(as_string=True, places=2)
    sequence = fields.Integer(validate=validate.Range(min=1, max=32767))
    is_required = fields.Boolean()
    school_id = fields.Raw(load_only=True, allow_none=True)


class GradingResolveSchema(Schema):
    class Meta:
        unknown = INCLUDE

    academic_year_id = fields.UUID(load_default=None)
    id_annee = fields.UUID(load_default=None)
    program_id = fields.UUID(load_default=None)
    id_program = fields.UUID(load_default=None)
    level_id = fields.UUID(allow_none=True, load_default=None)
    id_niveau = fields.UUID(allow_none=True, load_default=None)
    class_id = fields.UUID(allow_none=True, load_default=None)
    subject_id = fields.UUID(allow_none=True, load_default=None)
    id_matiere = fields.UUID(allow_none=True, load_default=None)
    academic_period_id = fields.UUID(allow_none=True, load_default=None)
    diagnostic = fields.Boolean(load_default=False)
    school_id = fields.Raw(load_only=True, allow_none=True)


class GradingStatusFilterSchema(Schema):
    status = fields.String(validate=validate.OneOf(list(GRADING_RULESET_STATUSES)))
