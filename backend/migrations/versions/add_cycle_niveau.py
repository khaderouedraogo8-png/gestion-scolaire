"""Ajoute la colonne cycle à niveau_etude."""
revision = "add_cycle_niveau"
down_revision = "initial"
branch_labels = None
depends_on = None


def upgrade():
    from alembic import op
    import sqlalchemy as sa

    op.add_column(
        "niveau_etude",
        sa.Column("cycle", sa.String(length=20), server_default="premier", nullable=False),
    )
    op.create_check_constraint(
        "ck_niveau_etude_cycle",
        "niveau_etude",
        "cycle IN ('premier', 'second')",
    )
    op.execute(
        """
        UPDATE niveau_etude SET cycle = 'premier'
        WHERE libelle IN ('6ème', '5ème', '4ème', '3ème', '6eme', '5eme', '4eme', '3eme');
        UPDATE niveau_etude SET cycle = 'second'
        WHERE libelle IN ('Seconde', 'Première', 'Terminale', '2nde', '1ère', '1ere');
        """
    )


def downgrade():
    from alembic import op

    op.drop_constraint("ck_niveau_etude_cycle", "niveau_etude", type_="check")
    op.drop_column("niveau_etude", "cycle")
