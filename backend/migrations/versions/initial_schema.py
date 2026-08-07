"""Revision ID placeholder — schéma appliqué via schema_v2_mono_etablissement.sql."""
revision = "initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Le schéma PostgreSQL est appliqué via docker-entrypoint-initdb.d
    # ou manuellement : psql -f database/schema_v2_mono_etablissement.sql
    # Alembic est configuré pour les migrations futures.
    pass


def downgrade():
    pass
