"""Deerflow depth — rôles surveillant/eleve + lien eleve.id_utilisateur.

Étend utilisateur_role_check et ajoute eleve.id_utilisateur (nullable)
pour le portail élève authentifié.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "deerflow_depth_roles"
down_revision = "deerflow_full_delivery"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Rôles surveillant + eleve
    op.drop_constraint("utilisateur_role_check", "utilisateur", type_="check")
    op.create_check_constraint(
        "utilisateur_role_check",
        "utilisateur",
        "role IN ("
        "'administrateur', 'directeur', 'enseignant', 'agent_comptable', "
        "'secretariat', 'surveillant', 'parent', 'eleve', 'super_admin')",
    )

    # eleve.id_utilisateur — idempotent
    exists = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='eleve' AND column_name='id_utilisateur'"
        )
    ).fetchone()
    if not exists:
        op.add_column(
            "eleve",
            sa.Column("id_utilisateur", UUID(as_uuid=True), nullable=True),
        )
        op.create_index("ix_eleve_id_utilisateur", "eleve", ["id_utilisateur"])


def downgrade():
    op.drop_index("ix_eleve_id_utilisateur", table_name="eleve")
    op.drop_column("eleve", "id_utilisateur")

    op.drop_constraint("utilisateur_role_check", "utilisateur", type_="check")
    op.create_check_constraint(
        "utilisateur_role_check",
        "utilisateur",
        "role IN ("
        "'administrateur', 'directeur', 'enseignant', 'agent_comptable', "
        "'secretariat', 'parent', 'super_admin')",
    )
