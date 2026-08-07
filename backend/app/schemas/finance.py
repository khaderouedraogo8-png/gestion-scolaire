"""Schémas finance."""
from marshmallow import Schema, fields, validate


class FraisScolaireSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_niveau = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)
    motif = fields.String(required=True)
    montant_total = fields.Decimal(required=True)


class EcheancePaiementSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_frais = fields.UUID(required=True)
    libelle = fields.String(allow_none=True)
    montant = fields.Decimal(required=True)
    date_echeance = fields.Date(required=True)


class PaiementSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)
    id_echeance = fields.UUID(allow_none=True)
    motif = fields.String(required=True)
    montant_verse = fields.Decimal(required=True)
    mode_paiement = fields.String(allow_none=True)
    numero_recu = fields.String(dump_only=True)
    annule = fields.Boolean(dump_only=True)
    motif_annulation = fields.String(allow_none=True)
    date_paiement = fields.DateTime(dump_only=True)


class PaiementCreateSchema(Schema):
    id_eleve = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)
    id_echeance = fields.UUID(allow_none=True)
    motif = fields.String(required=True)
    montant_verse = fields.Decimal(required=True, validate=validate.Range(min=0.01))
    mode_paiement = fields.String(allow_none=True)


class AnnulationPaiementSchema(Schema):
    motif_annulation = fields.String(required=True)
