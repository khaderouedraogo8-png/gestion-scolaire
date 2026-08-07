"""Schémas emploi du temps."""
from marshmallow import Schema, fields, validate


class EnseignantSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_utilisateur = fields.UUID(allow_none=True)
    nom = fields.String(required=True)
    prenom = fields.String(required=True)
    specialite = fields.String(allow_none=True)
    type_contrat = fields.String(allow_none=True)
    taux_horaire = fields.Decimal(allow_none=True)
    telephone = fields.String(allow_none=True)
    email = fields.Email(allow_none=True)


class AffectationEnseignantSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_enseignant = fields.UUID(required=True)
    id_classe = fields.UUID(required=True)
    id_matiere = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)
    volume_horaire_hebdo = fields.Decimal(allow_none=True)


class SalleSchema(Schema):
    id = fields.UUID(dump_only=True)
    libelle = fields.String(required=True)
    capacite = fields.Integer(allow_none=True)


class CreneauEmploiTempsSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_affectation = fields.UUID(required=True)
    id_salle = fields.UUID(allow_none=True)
    jour_semaine = fields.Integer(required=True, validate=validate.Range(min=1, max=7))
    heure_debut = fields.Time(required=True)
    heure_fin = fields.Time(required=True)
