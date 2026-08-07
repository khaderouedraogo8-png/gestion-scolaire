"""Schémas Marshmallow — authentification."""
from marshmallow import Schema, fields, validate


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=1))


class ChangePasswordSchema(Schema):
    ancien_mot_de_passe = fields.String(required=True)
    nouveau_mot_de_passe = fields.String(required=True, validate=validate.Length(min=8))


class UserSchema(Schema):
    id = fields.UUID(dump_only=True)
    nom = fields.String(required=True)
    prenom = fields.String(required=True)
    email = fields.Email(required=True)
    telephone = fields.String(allow_none=True)
    role = fields.String(required=True)
    actif = fields.Boolean(dump_only=True)
    doit_changer_mdp = fields.Boolean(dump_only=True)


class TokenResponseSchema(Schema):
    access_token = fields.String()
    user = fields.Nested(UserSchema)
    doit_changer_mdp = fields.Boolean()
