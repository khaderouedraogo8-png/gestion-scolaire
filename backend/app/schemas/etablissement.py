"""Schémas établissement, année, trimestre, niveau, classe."""
from marshmallow import Schema, fields, validate


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


class AnneeScolaireSchema(Schema):
    id = fields.UUID(dump_only=True)
    libelle = fields.String(required=True)
    date_debut = fields.Date(required=True)
    date_fin = fields.Date(required=True)
    est_active = fields.Boolean(load_default=False)


class TrimestreSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_annee = fields.UUID(required=True)
    numero = fields.Integer(required=True, validate=validate.OneOf([1, 2, 3]))
    date_debut = fields.Date(required=True)
    date_fin = fields.Date(required=True)


class NiveauEtudeSchema(Schema):
    id = fields.UUID(dump_only=True)
    libelle = fields.String(required=True)
    ordre = fields.Integer(allow_none=True)


class ClasseSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_niveau = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)
    libelle = fields.String(required=True)
    id_professeur_principal = fields.UUID(allow_none=True)
    capacite_max = fields.Integer(load_default=50)
