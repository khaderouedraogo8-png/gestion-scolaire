"""Deerflow full delivery — modules A/B foundation tables + matricule_sequence.

Revision ID: deerflow_full_delivery
Revises: uemoa_livraison_wave1
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "deerflow_full_delivery"
down_revision = "uemoa_livraison_wave1"
branch_labels = None
depends_on = None


def _school_id_col():
    return sa.Column(
        "school_id",
        UUID(as_uuid=True),
        sa.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
    )


def _uuid_pk():
    return sa.Column("id", UUID(as_uuid=True), primary_key=True)


def _ts_created():
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade():
    op.execute(
        "ALTER TABLE etablissement "
        "ADD COLUMN IF NOT EXISTS matricule_sequence INTEGER NOT NULL DEFAULT 0"
    )

    # --- Admissions & fratrie ---
    op.create_table(
        "admission_dossier",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_annee", UUID(as_uuid=True), nullable=True),
        sa.Column("nom", sa.String(100), nullable=False),
        sa.Column("prenom", sa.String(100), nullable=False),
        sa.Column("sexe", sa.String(1), nullable=True),
        sa.Column("date_naissance", sa.Date(), nullable=True),
        sa.Column("lieu_naissance", sa.String(100), nullable=True),
        sa.Column("telephone_parent", sa.String(30), nullable=True),
        sa.Column("email_parent", sa.String(150), nullable=True),
        sa.Column("niveau_demande", sa.String(50), nullable=True),
        sa.Column("statut", sa.String(30), nullable=False, server_default="brouillon"),
        sa.Column("pieces", JSONB, nullable=True),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        _ts_created(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_admission_dossier_school_id", "admission_dossier", ["school_id"])
    op.create_index(
        "ix_admission_dossier_school_statut",
        "admission_dossier",
        ["school_id", "statut"],
    )

    op.create_table(
        "fratrie",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("libelle", sa.String(120), nullable=True),
        sa.Column("id_parent_principal", UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        _ts_created(),
    )
    op.create_index("ix_fratrie_school_id", "fratrie", ["school_id"])

    op.create_table(
        "eleve_fratrie",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column("id_fratrie", UUID(as_uuid=True), nullable=False),
        sa.UniqueConstraint("id_eleve", "id_fratrie", name="uq_eleve_fratrie_pair"),
        sa.ForeignKeyConstraint(
            ["id_fratrie"],
            ["fratrie.id"],
            ondelete="CASCADE",
            name="fk_eleve_fratrie_fratrie",
        ),
    )
    op.create_index("ix_eleve_fratrie_school_id", "eleve_fratrie", ["school_id"])
    op.create_index("ix_eleve_fratrie_id_eleve", "eleve_fratrie", ["id_eleve"])
    op.create_index("ix_eleve_fratrie_id_fratrie", "eleve_fratrie", ["id_fratrie"])

    op.create_table(
        "remise_regle",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("libelle", sa.String(120), nullable=False),
        sa.Column("type_remise", sa.String(20), nullable=False, server_default="pourcent"),
        sa.Column("valeur", sa.Numeric(12, 2), nullable=False),
        sa.Column("condition_type", sa.String(40), nullable=True),
        sa.Column("condition_valeur", sa.String(80), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priorite", sa.Integer(), nullable=False, server_default="0"),
        _ts_created(),
        sa.UniqueConstraint("school_id", "code", name="uq_remise_regle_school_code"),
    )
    op.create_index("ix_remise_regle_school_id", "remise_regle", ["school_id"])

    # --- Conseil de classe & passage ---
    op.create_table(
        "conseil_classe_session",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_classe", UUID(as_uuid=True), nullable=False),
        sa.Column("id_trimestre", UUID(as_uuid=True), nullable=True),
        sa.Column("id_annee", UUID(as_uuid=True), nullable=True),
        sa.Column("date_session", sa.Date(), nullable=False),
        sa.Column("statut", sa.String(30), nullable=False, server_default="planifie"),
        sa.Column("pv_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("anime_par", UUID(as_uuid=True), nullable=True),
        _ts_created(),
    )
    op.create_index(
        "ix_conseil_classe_session_school_id",
        "conseil_classe_session",
        ["school_id"],
    )
    op.create_index(
        "ix_conseil_classe_session_classe",
        "conseil_classe_session",
        ["school_id", "id_classe"],
    )

    op.create_table(
        "decision_passage",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column("id_annee", UUID(as_uuid=True), nullable=False),
        sa.Column("id_session", UUID(as_uuid=True), nullable=True),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("mention", sa.String(40), nullable=True),
        sa.Column("commentaire", sa.Text(), nullable=True),
        sa.Column("valide_par", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "valide_le",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        _ts_created(),
        sa.ForeignKeyConstraint(
            ["id_session"],
            ["conseil_classe_session.id"],
            ondelete="SET NULL",
            name="fk_decision_passage_session",
        ),
        sa.UniqueConstraint(
            "school_id",
            "id_eleve",
            "id_annee",
            name="uq_decision_passage_eleve_annee",
        ),
    )
    op.create_index("ix_decision_passage_school_id", "decision_passage", ["school_id"])
    op.create_index("ix_decision_passage_id_eleve", "decision_passage", ["id_eleve"])

    # --- Absences & décrochage ---
    op.create_table(
        "absence_justificatif",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_absence", UUID(as_uuid=True), nullable=False),
        sa.Column("fichier_url", sa.Text(), nullable=True),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column("valide", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("valide_par", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "date_depot",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "valide_le",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_absence_justificatif_school_id",
        "absence_justificatif",
        ["school_id"],
    )
    op.create_index(
        "ix_absence_justificatif_id_absence",
        "absence_justificatif",
        ["id_absence"],
    )

    op.create_table(
        "alerte_decrochage",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column("type_alerte", sa.String(40), nullable=False),
        sa.Column("niveau", sa.String(20), nullable=False, server_default="moyen"),
        sa.Column("score", sa.Numeric(8, 2), nullable=True),
        sa.Column("statut", sa.String(30), nullable=False, server_default="ouverte"),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("traite_par", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "traite_le",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        _ts_created(),
    )
    op.create_index("ix_alerte_decrochage_school_id", "alerte_decrochage", ["school_id"])
    op.create_index(
        "ix_alerte_decrochage_eleve_statut",
        "alerte_decrochage",
        ["school_id", "id_eleve", "statut"],
    )

    # --- EDT ---
    op.create_table(
        "edt_publication",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_annee", UUID(as_uuid=True), nullable=False),
        sa.Column("libelle", sa.String(80), nullable=True),
        sa.Column("semaine", sa.Integer(), nullable=True),
        sa.Column("date_debut", sa.Date(), nullable=True),
        sa.Column("date_fin", sa.Date(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "publie_le",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("publie_par", UUID(as_uuid=True), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_edt_publication_school_id", "edt_publication", ["school_id"])
    op.create_index(
        "ix_edt_publication_annee",
        "edt_publication",
        ["school_id", "id_annee"],
    )

    op.create_table(
        "remplacement_enseignant",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_enseignant_absent", UUID(as_uuid=True), nullable=False),
        sa.Column("id_enseignant_remplacant", UUID(as_uuid=True), nullable=True),
        sa.Column("id_creneau", UUID(as_uuid=True), nullable=True),
        sa.Column("date_remplacement", sa.Date(), nullable=False),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column("statut", sa.String(30), nullable=False, server_default="planifie"),
        _ts_created(),
    )
    op.create_index(
        "ix_remplacement_enseignant_school_id",
        "remplacement_enseignant",
        ["school_id"],
    )
    op.create_index(
        "ix_remplacement_enseignant_date",
        "remplacement_enseignant",
        ["school_id", "date_remplacement"],
    )

    # --- Comptabilité & paie ---
    op.create_table(
        "ecriture_comptable",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("date_ecriture", sa.Date(), nullable=False),
        sa.Column("libelle", sa.String(200), nullable=False),
        sa.Column("compte_debit", sa.String(16), nullable=False),
        sa.Column("compte_credit", sa.String(16), nullable=False),
        sa.Column("montant", sa.Numeric(14, 2), nullable=False),
        sa.Column("reference", sa.String(60), nullable=True),
        sa.Column("id_paiement", UUID(as_uuid=True), nullable=True),
        sa.Column("journal", sa.String(20), nullable=True),
        sa.Column("piece_url", sa.Text(), nullable=True),
        sa.Column("saisi_par", UUID(as_uuid=True), nullable=True),
        _ts_created(),
    )
    op.create_index("ix_ecriture_comptable_school_id", "ecriture_comptable", ["school_id"])
    op.create_index(
        "ix_ecriture_comptable_date",
        "ecriture_comptable",
        ["school_id", "date_ecriture"],
    )

    op.create_table(
        "paie_periode",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("libelle", sa.String(80), nullable=False),
        sa.Column("date_debut", sa.Date(), nullable=False),
        sa.Column("date_fin", sa.Date(), nullable=False),
        sa.Column("statut", sa.String(30), nullable=False, server_default="ouverte"),
        sa.Column(
            "cloture_le",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        _ts_created(),
    )
    op.create_index("ix_paie_periode_school_id", "paie_periode", ["school_id"])

    op.create_table(
        "paie_ligne",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_periode", UUID(as_uuid=True), nullable=False),
        sa.Column("id_utilisateur", UUID(as_uuid=True), nullable=True),
        sa.Column("id_enseignant", UUID(as_uuid=True), nullable=True),
        sa.Column("matricule", sa.String(40), nullable=True),
        sa.Column("brut", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("retenues", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("net", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("details", JSONB, nullable=True),
        _ts_created(),
        sa.ForeignKeyConstraint(
            ["id_periode"],
            ["paie_periode.id"],
            ondelete="CASCADE",
            name="fk_paie_ligne_periode",
        ),
    )
    op.create_index("ix_paie_ligne_school_id", "paie_ligne", ["school_id"])
    op.create_index("ix_paie_ligne_id_periode", "paie_ligne", ["id_periode"])

    # --- Cantine ---
    op.create_table(
        "cantine_abonnement",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column("id_annee", UUID(as_uuid=True), nullable=True),
        sa.Column("formule", sa.String(40), nullable=False, server_default="standard"),
        sa.Column("montant", sa.Numeric(12, 2), nullable=True),
        sa.Column("date_debut", sa.Date(), nullable=False),
        sa.Column("date_fin", sa.Date(), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts_created(),
    )
    op.create_index("ix_cantine_abonnement_school_id", "cantine_abonnement", ["school_id"])
    op.create_index("ix_cantine_abonnement_id_eleve", "cantine_abonnement", ["id_eleve"])

    op.create_table(
        "cantine_presence",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column("date_presence", sa.Date(), nullable=False),
        sa.Column("repas", sa.String(20), nullable=False, server_default="midi"),
        sa.Column("present", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "school_id",
            "id_eleve",
            "date_presence",
            "repas",
            name="uq_cantine_presence_eleve_date_repas",
        ),
    )
    op.create_index("ix_cantine_presence_school_id", "cantine_presence", ["school_id"])
    op.create_index(
        "ix_cantine_presence_date",
        "cantine_presence",
        ["school_id", "date_presence"],
    )

    # --- Transport ---
    op.create_table(
        "transport_itineraire",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("libelle", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts_created(),
    )
    op.create_index(
        "ix_transport_itineraire_school_id",
        "transport_itineraire",
        ["school_id"],
    )

    op.create_table(
        "transport_arret",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_itineraire", UUID(as_uuid=True), nullable=False),
        sa.Column("libelle", sa.String(120), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("heure_passage", sa.String(10), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_itineraire"],
            ["transport_itineraire.id"],
            ondelete="CASCADE",
            name="fk_transport_arret_itineraire",
        ),
    )
    op.create_index("ix_transport_arret_school_id", "transport_arret", ["school_id"])
    op.create_index("ix_transport_arret_itineraire", "transport_arret", ["id_itineraire"])

    op.create_table(
        "transport_eleve",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column("id_itineraire", UUID(as_uuid=True), nullable=False),
        sa.Column("id_arret", UUID(as_uuid=True), nullable=True),
        sa.Column("id_annee", UUID(as_uuid=True), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts_created(),
        sa.ForeignKeyConstraint(
            ["id_itineraire"],
            ["transport_itineraire.id"],
            ondelete="CASCADE",
            name="fk_transport_eleve_itineraire",
        ),
        sa.ForeignKeyConstraint(
            ["id_arret"],
            ["transport_arret.id"],
            ondelete="SET NULL",
            name="fk_transport_eleve_arret",
        ),
    )
    op.create_index("ix_transport_eleve_school_id", "transport_eleve", ["school_id"])
    op.create_index("ix_transport_eleve_id_eleve", "transport_eleve", ["id_eleve"])

    # --- Internat ---
    op.create_table(
        "internat_chambre",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("batiment", sa.String(60), nullable=True),
        sa.Column("numero", sa.String(30), nullable=False),
        sa.Column("capacite", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("genre", sa.String(10), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint(
            "school_id",
            "batiment",
            "numero",
            name="uq_internat_chambre_batiment_numero",
        ),
    )
    op.create_index("ix_internat_chambre_school_id", "internat_chambre", ["school_id"])

    op.create_table(
        "internat_affectation",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_chambre", UUID(as_uuid=True), nullable=False),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column("id_annee", UUID(as_uuid=True), nullable=True),
        sa.Column("date_debut", sa.Date(), nullable=False),
        sa.Column("date_fin", sa.Date(), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts_created(),
        sa.ForeignKeyConstraint(
            ["id_chambre"],
            ["internat_chambre.id"],
            ondelete="CASCADE",
            name="fk_internat_affectation_chambre",
        ),
    )
    op.create_index(
        "ix_internat_affectation_school_id",
        "internat_affectation",
        ["school_id"],
    )
    op.create_index(
        "ix_internat_affectation_id_eleve",
        "internat_affectation",
        ["id_eleve"],
    )

    # --- Infirmerie & bibliothèque ---
    op.create_table(
        "infirmiere_soin",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "date_soin",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("motif", sa.Text(), nullable=False),
        sa.Column("traitement", sa.Text(), nullable=True),
        sa.Column("soigne_par", UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        _ts_created(),
    )
    op.create_index("ix_infirmiere_soin_school_id", "infirmiere_soin", ["school_id"])
    op.create_index("ix_infirmiere_soin_id_eleve", "infirmiere_soin", ["id_eleve"])

    op.create_table(
        "bibliotheque_livre",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("isbn", sa.String(20), nullable=True),
        sa.Column("titre", sa.String(200), nullable=False),
        sa.Column("auteur", sa.String(150), nullable=True),
        sa.Column("categorie", sa.String(60), nullable=True),
        sa.Column("exemplaires", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("disponibles", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts_created(),
    )
    op.create_index("ix_bibliotheque_livre_school_id", "bibliotheque_livre", ["school_id"])
    op.create_index(
        "ix_bibliotheque_livre_titre",
        "bibliotheque_livre",
        ["school_id", "titre"],
    )

    op.create_table(
        "bibliotheque_pret",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_livre", UUID(as_uuid=True), nullable=False),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column("date_pret", sa.Date(), nullable=False),
        sa.Column("date_retour_prevue", sa.Date(), nullable=True),
        sa.Column("date_retour_effective", sa.Date(), nullable=True),
        sa.Column("statut", sa.String(20), nullable=False, server_default="en_cours"),
        sa.Column("notes", sa.Text(), nullable=True),
        _ts_created(),
        sa.ForeignKeyConstraint(
            ["id_livre"],
            ["bibliotheque_livre.id"],
            ondelete="CASCADE",
            name="fk_bibliotheque_pret_livre",
        ),
    )
    op.create_index("ix_bibliotheque_pret_school_id", "bibliotheque_pret", ["school_id"])
    op.create_index("ix_bibliotheque_pret_id_eleve", "bibliotheque_pret", ["id_eleve"])
    op.create_index("ix_bibliotheque_pret_id_livre", "bibliotheque_pret", ["id_livre"])

    # --- RH ---
    op.create_table(
        "rh_contrat",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_utilisateur", UUID(as_uuid=True), nullable=True),
        sa.Column("id_enseignant", UUID(as_uuid=True), nullable=True),
        sa.Column("type_contrat", sa.String(40), nullable=False),
        sa.Column("date_debut", sa.Date(), nullable=False),
        sa.Column("date_fin", sa.Date(), nullable=True),
        sa.Column("salaire_base", sa.Numeric(14, 2), nullable=True),
        sa.Column("statut", sa.String(30), nullable=False, server_default="actif"),
        sa.Column("poste", sa.String(80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        _ts_created(),
    )
    op.create_index("ix_rh_contrat_school_id", "rh_contrat", ["school_id"])
    op.create_index("ix_rh_contrat_id_utilisateur", "rh_contrat", ["id_utilisateur"])

    op.create_table(
        "rh_conge",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_utilisateur", UUID(as_uuid=True), nullable=False),
        sa.Column("type_conge", sa.String(40), nullable=False),
        sa.Column("date_debut", sa.Date(), nullable=False),
        sa.Column("date_fin", sa.Date(), nullable=False),
        sa.Column("statut", sa.String(30), nullable=False, server_default="demande"),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column("valide_par", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "valide_le",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        _ts_created(),
    )
    op.create_index("ix_rh_conge_school_id", "rh_conge", ["school_id"])
    op.create_index("ix_rh_conge_id_utilisateur", "rh_conge", ["id_utilisateur"])

    # --- Vie scolaire ---
    op.create_table(
        "visiteur",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("nom", sa.String(100), nullable=False),
        sa.Column("prenom", sa.String(100), nullable=True),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column("piece_identite", sa.String(60), nullable=True),
        sa.Column("telephone", sa.String(30), nullable=True),
        sa.Column(
            "heure_entree",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("heure_sortie", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accueilli_par", UUID(as_uuid=True), nullable=True),
        sa.Column("id_eleve_visite", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_visiteur_school_id", "visiteur", ["school_id"])
    op.create_index(
        "ix_visiteur_heure_entree",
        "visiteur",
        ["school_id", "heure_entree"],
    )

    op.create_table(
        "sortie_eleve",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "date_sortie",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column("autorise_par", UUID(as_uuid=True), nullable=True),
        sa.Column("recupere_par", sa.String(150), nullable=True),
        sa.Column("heure_retour", sa.DateTime(timezone=True), nullable=True),
        sa.Column("statut", sa.String(20), nullable=False, server_default="sorti"),
    )
    op.create_index("ix_sortie_eleve_school_id", "sortie_eleve", ["school_id"])
    op.create_index("ix_sortie_eleve_id_eleve", "sortie_eleve", ["id_eleve"])

    # --- Inventaire ---
    op.create_table(
        "inventaire_article",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("libelle", sa.String(150), nullable=False),
        sa.Column("categorie", sa.String(60), nullable=True),
        sa.Column("quantite", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("seuil_alerte", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unite", sa.String(20), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts_created(),
        sa.UniqueConstraint("school_id", "code", name="uq_inventaire_article_school_code"),
    )
    op.create_index("ix_inventaire_article_school_id", "inventaire_article", ["school_id"])

    op.create_table(
        "inventaire_mouvement",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_article", UUID(as_uuid=True), nullable=False),
        sa.Column("type_mouvement", sa.String(20), nullable=False),
        sa.Column("quantite", sa.Integer(), nullable=False),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column(
            "date_mouvement",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("effectue_par", UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_article"],
            ["inventaire_article.id"],
            ondelete="CASCADE",
            name="fk_inventaire_mouvement_article",
        ),
    )
    op.create_index(
        "ix_inventaire_mouvement_school_id",
        "inventaire_mouvement",
        ["school_id"],
    )
    op.create_index(
        "ix_inventaire_mouvement_id_article",
        "inventaire_mouvement",
        ["id_article"],
    )

    # --- E-learning ---
    op.create_table(
        "elearning_devoir",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_classe", UUID(as_uuid=True), nullable=True),
        sa.Column("id_matiere", UUID(as_uuid=True), nullable=True),
        sa.Column("titre", sa.String(200), nullable=False),
        sa.Column("consignes", sa.Text(), nullable=True),
        sa.Column("date_limite", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cree_par", UUID(as_uuid=True), nullable=True),
        sa.Column("publie", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts_created(),
    )
    op.create_index("ix_elearning_devoir_school_id", "elearning_devoir", ["school_id"])
    op.create_index("ix_elearning_devoir_id_classe", "elearning_devoir", ["id_classe"])

    op.create_table(
        "elearning_remise",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_devoir", UUID(as_uuid=True), nullable=False),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column("fichier_url", sa.Text(), nullable=True),
        sa.Column("contenu", sa.Text(), nullable=True),
        sa.Column(
            "date_remise",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("note", sa.Numeric(6, 2), nullable=True),
        sa.Column("commentaire", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_devoir"],
            ["elearning_devoir.id"],
            ondelete="CASCADE",
            name="fk_elearning_remise_devoir",
        ),
        sa.UniqueConstraint(
            "id_devoir",
            "id_eleve",
            name="uq_elearning_remise_devoir_eleve",
        ),
    )
    op.create_index("ix_elearning_remise_school_id", "elearning_remise", ["school_id"])
    op.create_index("ix_elearning_remise_id_devoir", "elearning_remise", ["id_devoir"])
    op.create_index("ix_elearning_remise_id_eleve", "elearning_remise", ["id_eleve"])

    op.create_table(
        "elearning_quiz",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("id_classe", UUID(as_uuid=True), nullable=True),
        sa.Column("id_matiere", UUID(as_uuid=True), nullable=True),
        sa.Column("titre", sa.String(200), nullable=False),
        sa.Column("questions", JSONB, nullable=True),
        sa.Column("duree_minutes", sa.Integer(), nullable=True),
        sa.Column("publie", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cree_par", UUID(as_uuid=True), nullable=True),
        _ts_created(),
    )
    op.create_index("ix_elearning_quiz_school_id", "elearning_quiz", ["school_id"])

    # --- OTP ---
    op.create_table(
        "otp_challenge",
        _uuid_pk(),
        _school_id_col(),
        sa.Column("canal", sa.String(20), nullable=False),
        sa.Column("destinataire", sa.String(150), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("purpose", sa.String(40), nullable=False, server_default="login"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id_utilisateur", UUID(as_uuid=True), nullable=True),
        _ts_created(),
    )
    op.create_index("ix_otp_challenge_school_id", "otp_challenge", ["school_id"])
    op.create_index(
        "ix_otp_challenge_destinataire",
        "otp_challenge",
        ["school_id", "destinataire", "purpose"],
    )
    op.create_index("ix_otp_challenge_expires_at", "otp_challenge", ["expires_at"])


def downgrade():
    tables = [
        "otp_challenge",
        "elearning_quiz",
        "elearning_remise",
        "elearning_devoir",
        "inventaire_mouvement",
        "inventaire_article",
        "sortie_eleve",
        "visiteur",
        "rh_conge",
        "rh_contrat",
        "bibliotheque_pret",
        "bibliotheque_livre",
        "infirmiere_soin",
        "internat_affectation",
        "internat_chambre",
        "transport_eleve",
        "transport_arret",
        "transport_itineraire",
        "cantine_presence",
        "cantine_abonnement",
        "paie_ligne",
        "paie_periode",
        "ecriture_comptable",
        "remplacement_enseignant",
        "edt_publication",
        "alerte_decrochage",
        "absence_justificatif",
        "decision_passage",
        "conseil_classe_session",
        "remise_regle",
        "eleve_fratrie",
        "fratrie",
        "admission_dossier",
    ]
    for name in tables:
        op.drop_table(name)

    op.execute("ALTER TABLE etablissement DROP COLUMN IF EXISTS matricule_sequence")
