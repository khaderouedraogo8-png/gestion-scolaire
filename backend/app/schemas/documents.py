"""Schémas documents et notifications."""
from marshmallow import Schema, fields, validate


class DocumentAdministratifSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    type_document = fields.String(
        validate=validate.OneOf(["carte_scolaire", "attestation_scolarite", "certificat", "diplome"])
    )
    date_emission = fields.Date(dump_only=True)
    date_expiration = fields.Date(allow_none=True)
    pdf_url = fields.String(dump_only=True)


class NotificationSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(allow_none=True)
    id_parent = fields.UUID(allow_none=True)
    canal = fields.String(validate=validate.OneOf(["sms", "email", "interne"]))
    type_notification = fields.String(allow_none=True)
    contenu = fields.String(allow_none=True)
    statut = fields.String(dump_only=True)
    tentative_count = fields.Integer(dump_only=True)
    lu_le = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class NotificationCreateSchema(Schema):
    id_eleve = fields.UUID(allow_none=True)
    id_parent = fields.UUID(allow_none=True)
    canal = fields.String(required=True, validate=validate.OneOf(["sms", "email", "interne"]))
    type_notification = fields.String(required=True)
    contenu = fields.String(required=True)


class DocumentGenerateSchema(Schema):
    id_eleve = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)


class CarteScolaireGenerateSchema(DocumentGenerateSchema):
    date_expiration = fields.Date(allow_none=True)


class DiplomeGenerateSchema(DocumentGenerateSchema):
    mention = fields.String(allow_none=True, validate=validate.Length(max=100))


class VerifierQRSchema(Schema):
    qr_data = fields.String(required=True, validate=validate.Length(min=1))
