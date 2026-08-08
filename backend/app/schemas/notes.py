"""Schémas notes, évaluations, bulletins."""
from marshmallow import Schema, fields, validate


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
        required=True, validate=validate.OneOf(["devoir", "examen", "interrogation"])
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
        required=True, validate=validate.OneOf(["devoir", "examen", "interrogation"])
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
    valeur_note = fields.Decimal(allow_none=True, validate=validate.Range(min=0, max=20))
    absent = fields.Boolean(load_default=False)
    appreciation = fields.String(allow_none=True)


class NoteInputSchema(Schema):
    id_eleve = fields.UUID(required=True)
    valeur_note = fields.Decimal(allow_none=True, validate=validate.Range(min=0, max=20))
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
