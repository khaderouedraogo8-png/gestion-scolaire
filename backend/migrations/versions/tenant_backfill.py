"""PR #9 step 2/5 — backfill school_id depuis ECOLE-EXISTANTE (par code)."""
revision = "tenant_backfill"
down_revision = "tenant_cols_nullable"
branch_labels = None
depends_on = None

DEFAULT_SCHOOL_CODE = "ECOLE-EXISTANTE"

TABLES = (
    "etablissement",
    "annee_scolaire",
    "niveau_etude",
    "eleve",
    "parent_tuteur",
    "enseignant",
    "matiere",
    "salle",
    "frais_scolaire",
    "classe",
    "evaluation",
    "paiement",
    "absence",
    "incident_disciplinaire",
    "document_administratif",
    "notification",
    "journal_audit",
    "bulletin",
    "inscription",
    "note",
    "affectation_enseignant",
)


def upgrade():
    import sqlalchemy as sa
    from alembic import op

    conn = op.get_bind()
    school_id = conn.execute(
        sa.text("SELECT id FROM schools WHERE code = :code"),
        {"code": DEFAULT_SCHOOL_CODE},
    ).scalar()

    if school_id is None:
        raise RuntimeError(
            f"École de migration introuvable (code={DEFAULT_SCHOOL_CODE}). "
            "Appliquer d'abord add_schools_tenant."
        )

    for table in TABLES:
        conn.execute(
            sa.text(
                f"UPDATE {table} SET school_id = :school_id WHERE school_id IS NULL"
            ),
            {"school_id": school_id},
        )

    # Utilisateurs encore sans tenant
    conn.execute(
        sa.text(
            "UPDATE utilisateur SET school_id = :school_id WHERE school_id IS NULL"
        ),
        {"school_id": school_id},
    )

    # Vérification stricte : aucune ligne métier sans school_id
    for table in TABLES:
        remaining = conn.execute(
            sa.text(f"SELECT COUNT(*) FROM {table} WHERE school_id IS NULL")
        ).scalar()
        if remaining:
            raise RuntimeError(f"Backfill incomplet : {table} a {remaining} school_id NULL")


def downgrade():
    # Intentionnel : ne pas nullifier les school_id métier (données de production).
    # Le downgrade de step 1 droppera les colonnes.
    pass
