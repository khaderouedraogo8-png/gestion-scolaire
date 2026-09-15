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

    op.get_bind()

    # Downgrade vers UNIQUE global impossible s'il existe des doublons cross-tenant.
    # On conserve une ligne par valeur (min id) pour permettre le rollback technique.
    for table, col, old_name, new_name in (
        ("paiement", "numero_recu", "paiement_numero_recu_key", "uq_paiement_school_numero_recu"),
        ("niveau_etude", "libelle", "niveau_etude_libelle_key", "uq_niveau_etude_school_libelle"),
        ("annee_scolaire", "libelle", "annee_scolaire_libelle_key", "uq_annee_scolaire_school_libelle"),
        ("eleve", "matricule", "eleve_matricule_key", "uq_eleve_school_matricule"),
    ):
        op.drop_constraint(new_name, table, type_="unique")
        # Ne pas supprimer de données métier : si doublons, le recreate unique échouera
        # volontairement (signal que le downgrade n'est pas sûr avec multi-écoles peuplées).
        try:
            op.create_unique_constraint(old_name, table, [col])
        except Exception as exc:
            raise RuntimeError(
                f"Downgrade UNIQUE global impossible sur {table}.{col} : "
                "des doublons cross-tenant existent. Nettoyer les écoles de test "
                "ou rester sur la révision tenant_rewrite_uniques."
            ) from exc
