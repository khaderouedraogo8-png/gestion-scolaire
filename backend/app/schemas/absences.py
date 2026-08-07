"""Schémas absences et discipline."""
from marshmallow import Schema, fields, validate


class AbsenceSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    id_creneau = fields.UUID(allow_none=True)
    date_absence = fields.Date(required=True)
    type_absence = fields.String(validate=validate.OneOf(["absence", "retard"]), allow_none=True)
    justifiee = fields.Boolean(load_default=False)
    motif = fields.String(allow_none=True)


class IncidentDisciplinaireSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    id_trimestre = fields.UUID(allow_none=True)
    type_incident = fields.String(
        validate=validate.OneOf(["avertissement", "blame", "exclusion_temporaire"]),
        allow_none=True,
    )
    description = fields.String(allow_none=True)
    date_incident = fields.Date(required=True)
