"""Schémas élèves, parents, inscriptions."""
from marshmallow import Schema, fields, validate


class ParentTuteurSchema(Schema):
    id = fields.UUID(dump_only=True)
    nom = fields.String(required=True)
    prenom = fields.String(required=True)
    lien_parente = fields.String(allow_none=True)
    telephone = fields.String(allow_none=True)
    email = fields.Email(allow_none=True)
    profession = fields.String(allow_none=True)
    adresse = fields.String(allow_none=True)
    tuteur_legal = fields.Boolean(load_default=False)


class EleveSchema(Schema):
    id = fields.UUID(dump_only=True)
    matricule = fields.String(dump_only=True)
    nom = fields.String(required=True)
    prenom = fields.String(required=True)
    sexe = fields.String(validate=validate.OneOf(["M", "F"]), allow_none=True)
    date_naissance = fields.Date(allow_none=True)
    lieu_naissance = fields.String(allow_none=True)
    adresse = fields.String(allow_none=True)
    photo_url = fields.String(allow_none=True)
    pieces_justificatives = fields.List(fields.Dict(), allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    # notes_medicales jamais dans les listes — uniquement via endpoint dédié


class EleveDetailSchema(EleveSchema):
    notes_medicales = fields.String(load_only=True)
    parents = fields.Nested(ParentTuteurSchema, many=True, dump_only=True)


class InscriptionSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(dump_only=True)
    id_classe = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)
    statut = fields.String(
        load_default="inscrit",
        validate=validate.OneOf(["inscrit", "abandon", "suspendu", "reinscrit", "diplome"]),
    )
    est_boursier = fields.Boolean(load_default=False)
    taux_reduction = fields.Decimal(load_default=0)
    date_inscription = fields.Date(dump_only=True)
    date_statut_maj = fields.Date(allow_none=True)
    classe_nom = fields.String(dump_only=True)
    annee_libelle = fields.String(dump_only=True)


class InscriptionCreateSchema(Schema):
    id_classe = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)
    statut = fields.String(
        load_default="inscrit",
        validate=validate.OneOf(["inscrit", "abandon", "suspendu", "reinscrit", "diplome"]),
    )
    est_boursier = fields.Boolean(load_default=False)
    taux_reduction = fields.Decimal(load_default=0)


class EleveListSchema(EleveSchema):
    statut = fields.String(dump_only=True)
    classe_nom = fields.String(dump_only=True)
    est_boursier = fields.Boolean(dump_only=True)


class EleveCreateSchema(Schema):
    nom = fields.String(required=True)
    prenom = fields.String(required=True)
    sexe = fields.String(validate=validate.OneOf(["M", "F"]), allow_none=True)
    date_naissance = fields.Date(allow_none=True)
    lieu_naissance = fields.String(allow_none=True)
    adresse = fields.String(allow_none=True)
    notes_medicales = fields.String(load_only=True, allow_none=True)
    id_classe = fields.UUID(required=True)
    id_annee = fields.UUID(required=True)
    parents = fields.Nested(ParentTuteurSchema, many=True, load_default=[])
