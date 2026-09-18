"""Deerflow e-learning LMS depth — ressources, tentatives quiz, barèmes.

down_revision: deerflow_depth_ops
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "deerflow_elearning_lms"
down_revision = "deerflow_depth_ops"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    def _has_column(table: str, column: str) -> bool:
        return bool(
            conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name=:t AND column_name=:c"
                ),
                {"t": table, "c": column},
            ).fetchone()
        )

    def _has_table(table: str) -> bool:
        return bool(
            conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name=:t"
                ),
                {"t": table},
            ).fetchone()
        )

    if not _has_column("elearning_devoir", "note_max"):
        op.add_column(
            "elearning_devoir",
            sa.Column(
                "note_max",
                sa.Numeric(6, 2),
                nullable=False,
                server_default="20",
            ),
        )
    if not _has_column("elearning_devoir", "pieces_jointes"):
        op.add_column(
            "elearning_devoir",
            sa.Column("pieces_jointes", JSONB(), nullable=True),
        )

    if not _has_column("elearning_remise", "statut"):
        op.add_column(
            "elearning_remise",
            sa.Column(
                "statut",
                sa.String(20),
                nullable=False,
                server_default="remise",
            ),
        )
    if not _has_column("elearning_remise", "notee_par"):
        op.add_column(
            "elearning_remise",
            sa.Column("notee_par", UUID(as_uuid=True), nullable=True),
        )
    if not _has_column("elearning_remise", "notee_le"):
        op.add_column(
            "elearning_remise",
            sa.Column("notee_le", sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_column("elearning_quiz", "note_max"):
        op.add_column(
            "elearning_quiz",
            sa.Column(
                "note_max",
                sa.Numeric(6, 2),
                nullable=False,
                server_default="20",
            ),
        )
    if not _has_column("elearning_quiz", "tentatives_max"):
        op.add_column(
            "elearning_quiz",
            sa.Column(
                "tentatives_max",
                sa.Integer(),
                nullable=False,
                server_default="3",
            ),
        )
    if not _has_column("elearning_quiz", "afficher_correction"):
        op.add_column(
            "elearning_quiz",
            sa.Column(
                "afficher_correction",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )

    if not _has_table("elearning_quiz_tentative"):
        op.create_table(
            "elearning_quiz_tentative",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("school_id", UUID(as_uuid=True), nullable=False),
            sa.Column("id_quiz", UUID(as_uuid=True), nullable=False),
            sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
            sa.Column("reponses", JSONB(), nullable=True),
            sa.Column("score_brut", sa.Numeric(8, 2), nullable=True),
            sa.Column("score_max", sa.Numeric(8, 2), nullable=True),
            sa.Column("note", sa.Numeric(6, 2), nullable=True),
            sa.Column("detail_correction", JSONB(), nullable=True),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["school_id"],
                ["schools.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["id_quiz"],
                ["elearning_quiz.id"],
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_elearning_quiz_tentative_school_id",
            "elearning_quiz_tentative",
            ["school_id"],
        )
        op.create_index(
            "ix_elearning_quiz_tentative_id_quiz",
            "elearning_quiz_tentative",
            ["id_quiz"],
        )
        op.create_index(
            "ix_elearning_quiz_tentative_id_eleve",
            "elearning_quiz_tentative",
            ["id_eleve"],
        )

    if not _has_table("elearning_ressource"):
        op.create_table(
            "elearning_ressource",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("school_id", UUID(as_uuid=True), nullable=False),
            sa.Column("id_classe", UUID(as_uuid=True), nullable=True),
            sa.Column("id_matiere", UUID(as_uuid=True), nullable=True),
            sa.Column("titre", sa.String(200), nullable=False),
            sa.Column(
                "type_ressource",
                sa.String(30),
                nullable=False,
                server_default="lien",
            ),
            sa.Column("url", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "publie",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column("cree_par", UUID(as_uuid=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["school_id"],
                ["schools.id"],
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_elearning_ressource_school_id",
            "elearning_ressource",
            ["school_id"],
        )
        op.create_index(
            "ix_elearning_ressource_id_classe",
            "elearning_ressource",
            ["id_classe"],
        )


def downgrade():
    op.drop_table("elearning_ressource")
    op.drop_table("elearning_quiz_tentative")
