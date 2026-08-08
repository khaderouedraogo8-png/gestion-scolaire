"""Schémas programme pédagogique."""
from marshmallow import Schema, fields, validate


class ProgrammeDevoirSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_classe = fields.UUID(required=True)
    id_matiere = fields.UUID(required=True)
    jour_semaine = fields.Integer(required=True, validate=validate.Range(min=1, max=7))
    frequence = fields.String(
        load_default="hebdomadaire",
        validate=validate.OneOf(["hebdomadaire", "quinzomadaire"]),
    )
    note = fields.String(allow_none=True)
    id_annee = fields.UUID(required=True)


class ProgrammeDevoirUpdateSchema(Schema):
    frequence = fields.String(validate=validate.OneOf(["hebdomadaire", "quinzomadaire"]))
    note = fields.String(allow_none=True)


class EvenementCalendrierSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_annee = fields.UUID(required=True)
    type_evenement = fields.String(
        required=True,
        validate=validate.OneOf(["ferie", "vacances", "rentree", "examen_officiel", "autre"]),
    )
    libelle = fields.String(required=True)
    date_debut = fields.Date(required=True)
    date_fin = fields.Date(required=True)
    bloque_programmation = fields.Boolean(load_default=True)


class SeanceCoursSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_classe = fields.UUID(required=True)
    id_matiere = fields.UUID(required=True)
    id_enseignant = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)
    date_seance = fields.Date(required=True)
    contenu = fields.String(required=True)
