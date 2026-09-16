"""PR #9 step 1/5 — colonnes school_id nullable sur tables métier."""
revision = "tenant_cols_nullable"
down_revision = "add_schools_tenant"
branch_labels = None
depends_on = None

# Tables avec school_id direct (racines + dénormalisées)
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
    from sqlalchemy.dialects.postgresql import UUID

    for table in TABLES:
        op.add_column(table, sa.Column("school_id", UUID(as_uuid=True), nullable=True))


def downgrade():
    from alembic import op

    for table in reversed(TABLES):
        op.drop_column(table, "school_id")
