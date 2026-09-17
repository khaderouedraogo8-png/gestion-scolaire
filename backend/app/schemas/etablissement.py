"""Schémas établissement, année, programme, période, niveau, classe."""
from marshmallow import Schema, fields, validate

PERIOD_TYPE_CHOICES = ["trimestre", "semestre", "custom", "annuel"]
PROGRAM_TYPE_CHOICES = ["general", "technique", "professionnel", "custom"]


class EtablissementSchema(Schema):
    id = fields.UUID(dump_only=True)
    nom = fields.String(required=True)
    sigle = fields.String(allow_none=True)
    adresse = fields.String(allow_none=True)
    telephone = fields.String(allow_none=True)
    email = fields.Email(allow_none=True)
    logo_url = fields.String(allow_none=True)
    type_etablissement = fields.String(allow_none=True)
    pays = fields.String(allow_none=True)
    ville = fields.String(allow_none=True)
    format_matricule = fields.String(load_default="{ANNEE}M-{SEQ}")
    devise = fields.String(load_default="XOF")
    bulletin_template = fields.String(
        load_default="BF",
        validate=validate.OneOf(["BF", "SN", "CI", "ML", "NE", "TG", "BJ", "GENERIC"]),
    )


class AnneeScolaireSchema(Schema):
    id = fields.UUID(dump_only=True)
    libelle = fields.String(required=True)
    date_debut = fields.Date(required=True)
    date_fin = fields.Date(required=True)
    est_active = fields.Boolean(load_default=False)


class ProgramCreateSchema(Schema):
    code = fields.String(required=True, validate=validate.Length(min=1, max=40))
    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    description = fields.String(allow_none=True)
    program_type = fields.String(load_default="general", validate=validate.OneOf(PROGRAM_TYPE_CHOICES))
    period_type_default = fields.String(
        load_default="trimestre", validate=validate.OneOf(PERIOD_TYPE_CHOICES)
    )
    is_active = fields.Boolean(load_default=True)
    # Capturé puis rejeté par reject_client_school_id (anti-spoof)
    school_id = fields.Raw(load_only=True, allow_none=True)


class ProgramUpdateSchema(Schema):
    code = fields.String(validate=validate.Length(min=1, max=40))
    name = fields.String(validate=validate.Length(min=1, max=150))
    description = fields.String(allow_none=True)
    program_type = fields.String(validate=validate.OneOf(PROGRAM_TYPE_CHOICES))
    period_type_default = fields.String(validate=validate.OneOf(PERIOD_TYPE_CHOICES))
    is_active = fields.Boolean()


class ProgramSchema(Schema):
    id = fields.UUID(dump_only=True)
    code = fields.String()
    name = fields.String()
    description = fields.String(allow_none=True)
    program_type = fields.String()
    period_type_default = fields.String()
    is_active = fields.Boolean()
    levels_count = fields.Integer(dump_only=True)
    classes_count = fields.Integer(dump_only=True)
    periods_count = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    message = fields.String(dump_only=True)
    dependencies = fields.Dict(dump_only=True)


class PeriodCreateSchema(Schema):
    id_annee = fields.UUID(required=True)
    id_program = fields.UUID(required=True)
    sequence = fields.Integer(required=True, validate=validate.Range(min=1))
    code = fields.String(validate=validate.Length(min=1, max=20))
    label = fields.String(validate=validate.Length(min=1, max=80))
    period_type = fields.String(load_default="trimestre", validate=validate.OneOf(PERIOD_TYPE_CHOICES))
    date_debut = fields.Date(required=True)
    date_fin = fields.Date(required=True)
    is_active = fields.Boolean(load_default=True)


class PeriodUpdateSchema(Schema):
    id_annee = fields.UUID()
    id_program = fields.UUID()
    sequence = fields.Integer(validate=validate.Range(min=1))
    code = fields.String(validate=validate.Length(min=1, max=20))
    label = fields.String(validate=validate.Length(min=1, max=80))
    period_type = fields.String(validate=validate.OneOf(PERIOD_TYPE_CHOICES))
    date_debut = fields.Date()
    date_fin = fields.Date()
    is_active = fields.Boolean()


class PeriodSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_annee = fields.UUID()
    id_program = fields.UUID()
    sequence = fields.Integer()
    code = fields.String()
    label = fields.String()
    period_type = fields.String()
    date_debut = fields.Date()
    date_fin = fields.Date()
    is_active = fields.Boolean()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class TrimestreSchema(Schema):
    """Façade legacy — numero dérivé de sequence (même service métier)."""

    id = fields.UUID(dump_only=True)
    id_annee = fields.UUID(required=True)
    numero = fields.Integer(required=True, validate=validate.Range(min=1))
    date_debut = fields.Date(required=True)
    date_fin = fields.Date(required=True)


class NiveauEtudeSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_program = fields.UUID(allow_none=True)
    libelle = fields.String(required=True)
    ordre = fields.Integer(allow_none=True)
    cycle = fields.String(load_default="premier", validate=validate.OneOf(["premier", "second"]))


class ClasseSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_niveau = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)
    id_program = fields.UUID(allow_none=True)
    libelle = fields.String(required=True)
    id_professeur_principal = fields.UUID(allow_none=True)
    capacite_max = fields.Integer(load_default=50)
