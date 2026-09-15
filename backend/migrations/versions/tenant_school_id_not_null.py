"""PR #9 step 5/5 — school_id NOT NULL sur tables métier (+ utilisateur)."""
revision = "tenant_school_id_not_null"
down_revision = "tenant_rewrite_uniques"
branch_labels = None
depends_on = None

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
    "utilisateur",
)


def upgrade():
    import sqlalchemy as sa
    from alembic import op
    from sqlalchemy.dialects.postgresql import UUID

    conn = op.get_bind()
    for table in TABLES:
        remaining = conn.execute(
            sa.text(f"SELECT COUNT(*) FROM {table} WHERE school_id IS NULL")
        ).scalar()
        if remaining:
            raise RuntimeError(
                f"Impossible NOT NULL : {table} a encore {remaining} school_id NULL"
            )
        op.alter_column(
            table,
            "school_id",
            existing_type=UUID(as_uuid=True),
            nullable=False,
        )


def downgrade():
    from alembic import op
    from sqlalchemy.dialects.postgresql import UUID

    for table in reversed(TABLES):
        op.alter_column(
            table,
            "school_id",
            existing_type=UUID(as_uuid=True),
            nullable=True,
        )
