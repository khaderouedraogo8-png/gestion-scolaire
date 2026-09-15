"""PR #9 step 4/5 — UNIQUE tenant-locaux (school_id, …)."""
revision = "tenant_rewrite_uniques"
down_revision = "tenant_fks_indexes"
branch_labels = None
depends_on = None


def upgrade():
    from alembic import op

    # eleve.matricule global → (school_id, matricule)
    op.drop_constraint("eleve_matricule_key", "eleve", type_="unique")
    op.create_unique_constraint("uq_eleve_school_matricule", "eleve", ["school_id", "matricule"])

    # annee_scolaire.libelle global → (school_id, libelle)
    op.drop_constraint("annee_scolaire_libelle_key", "annee_scolaire", type_="unique")
    op.create_unique_constraint(
        "uq_annee_scolaire_school_libelle", "annee_scolaire", ["school_id", "libelle"]
    )

    # niveau_etude.libelle global → (school_id, libelle)
    op.drop_constraint("niveau_etude_libelle_key", "niveau_etude", type_="unique")
    op.create_unique_constraint(
        "uq_niveau_etude_school_libelle", "niveau_etude", ["school_id", "libelle"]
    )

    # paiement.numero_recu global → (school_id, numero_recu)
    op.drop_constraint("paiement_numero_recu_key", "paiement", type_="unique")
    op.create_unique_constraint(
        "uq_paiement_school_numero_recu", "paiement", ["school_id", "numero_recu"]
    )

    # utilisateur.email reste UNIQUE global (volontaire)


def downgrade():
    from alembic import op

    op.drop_constraint("uq_paiement_school_numero_recu", "paiement", type_="unique")
    op.create_unique_constraint("paiement_numero_recu_key", "paiement", ["numero_recu"])

    op.drop_constraint("uq_niveau_etude_school_libelle", "niveau_etude", type_="unique")
    op.create_unique_constraint("niveau_etude_libelle_key", "niveau_etude", ["libelle"])

    op.drop_constraint("uq_annee_scolaire_school_libelle", "annee_scolaire", type_="unique")
    op.create_unique_constraint("annee_scolaire_libelle_key", "annee_scolaire", ["libelle"])

    op.drop_constraint("uq_eleve_school_matricule", "eleve", type_="unique")
    op.create_unique_constraint("eleve_matricule_key", "eleve", ["matricule"])
