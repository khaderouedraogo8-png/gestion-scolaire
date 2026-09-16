"""Schémas notes, évaluations, bulletins."""
from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate, validates_schema

# type_evaluation : validé contre le catalogue tenant (PR15-A), pas OneOf système.


class MatiereSchema(Schema):
    id = fields.UUID(dump_only=True)
    libelle = fields.String(required=True)
    code = fields.String(allow_none=True)


class CoefficientMatiereSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_matiere = fields.UUID(required=True)
    id_niveau = fields.UUID(required=True)
    coefficient = fields.Decimal(required=True)


class EvaluationSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_classe = fields.UUID(required=True)
    id_matiere = fields.UUID(required=True)
    id_trimestre = fields.UUID(required=True)
    id_enseignant = fields.UUID(required=True)
    type_evaluation = fields.String(
        required=True, validate=validate.Length(min=1, max=20)
    )
    coefficient = fields.Decimal(load_default=1)
    date_evaluation = fields.Date(required=True)
    libelle = fields.String(allow_none=True)
    statut_publication = fields.String(dump_only=True)
    statut_saisie = fields.String(dump_only=True)


class EvaluationCreateSchema(Schema):
    id_classe = fields.UUID(required=True)
    id_matiere = fields.UUID(required=True)
    id_trimestre = fields.UUID(required=True)
    id_enseignant = fields.UUID(required=False, allow_none=True)
    type_evaluation = fields.String(
        required=True, validate=validate.Length(min=1, max=20)
    )
    coefficient = fields.Decimal(load_default=1)
    date_evaluation = fields.Date(required=True)
    libelle = fields.String(allow_none=True)
    statut_publication = fields.String(dump_only=True)
    statut_saisie = fields.String(dump_only=True)


class NoteSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_evaluation = fields.UUID(required=True)
    id_eleve = fields.UUID(required=True)
    # Échelle réelle = scale_max du ruleset (PR15-A) — pas de plafond /20 hardcodé
    valeur_note = fields.Decimal(allow_none=True, validate=validate.Range(min=0))
    absent = fields.Boolean(load_default=False)
    appreciation = fields.String(allow_none=True)


class NoteInputSchema(Schema):
    id_eleve = fields.UUID(required=True)
    valeur_note = fields.Decimal(allow_none=True, validate=validate.Range(min=0))
    absent = fields.Boolean(load_default=False)
    appreciation = fields.String(allow_none=True)


class NoteBatchSchema(Schema):
    notes = fields.Nested(NoteInputSchema, many=True, required=True)


class BulletinSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    id_trimestre = fields.UUID(required=True)
    moyenne_generale = fields.Decimal(dump_only=True)
    rang = fields.Integer(dump_only=True)
    effectif_classe = fields.Integer(dump_only=True)
    moyenne_classe = fields.Decimal(dump_only=True)
    mention = fields.String(dump_only=True)
    appreciation_generale = fields.String(allow_none=True)
    statut = fields.String(dump_only=True)
    pdf_url = fields.String(dump_only=True)
    rulesets_snapshot = fields.Raw(dump_only=True)
    results_calculated_at = fields.DateTime(dump_only=True)


class GenererBulletinSchema(Schema):
    id_eleve = fields.UUID(required=False, allow_none=True)
    id_classe = fields.UUID(required=False, allow_none=True)
    id_trimestre = fields.UUID(required=True)

    @validates_schema
    def require_eleve_or_classe(self, data, **kwargs):
        if not data.get("id_eleve") and not data.get("id_classe"):
            raise ValidationError(
                "id_eleve ou id_classe requis.",
                field_names=["id_eleve", "id_classe"],
            )


class BulletinPatchSchema(Schema):
    appreciation_generale = fields.String(allow_none=True, validate=validate.Length(max=2000))


class AcademicResultsQuerySchema(Schema):
    id_eleve = fields.UUID(required=True)
    id_classe = fields.UUID(required=True)
    id_period = fields.UUID(required=True)


class AcademicResultsRecalcSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id_eleve = fields.UUID(required=False, allow_none=True)
    id_classe = fields.UUID(required=True)
    id_period = fields.UUID(required=True)
