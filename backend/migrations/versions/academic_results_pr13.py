"""PR #13 — persist academic subject results + bulletin ruleset snapshot.

Creates academic_subject_result and extends bulletin with rulesets_snapshot /
results_calculated_at for calculation provenance.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "academic_results_pr13"
down_revision = "grading_calc_pr12_step4"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    before = {
        "notes": conn.execute(sa.text("SELECT COUNT(*) FROM note")).scalar(),
        "bulletins": conn.execute(sa.text("SELECT COUNT(*) FROM bulletin")).scalar(),
        "evaluations": conn.execute(sa.text("SELECT COUNT(*) FROM evaluation")).scalar(),
    }

    op.create_table(
        "academic_subject_result",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column(
            "school_id",
            UUID(as_uuid=True),
            sa.ForeignKey("schools.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
        sa.Column("id_classe", UUID(as_uuid=True), nullable=False),
        sa.Column("id_matiere", UUID(as_uuid=True), nullable=False),
        sa.Column("id_period", UUID(as_uuid=True), nullable=False),
        sa.Column("moyenne", sa.Numeric(6, 2)),
        sa.Column("coefficient", sa.Numeric(4, 2), nullable=False, server_default="1"),
        sa.Column("ruleset_id", UUID(as_uuid=True)),
        sa.Column("ruleset_version", sa.Integer()),
        sa.Column("ruleset_code", sa.String(40)),
        sa.Column("incomplete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("incomplete_reason", sa.String(255)),
        sa.Column("source", sa.String(20), nullable=False, server_default="rules_engine"),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("calculation_trace", JSONB),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "source IN ('rules_engine', 'legacy')",
            name="ck_academic_subject_result_source",
        ),
        sa.UniqueConstraint(
            "school_id",
            "id_eleve",
            "id_classe",
            "id_matiere",
            "id_period",
            name="uq_academic_subject_result_scope",
        ),
        sa.UniqueConstraint("id", "school_id", name="uq_academic_subject_result_id_school"),
        sa.ForeignKeyConstraint(
            ["id_eleve", "school_id"],
            ["eleve.id", "eleve.school_id"],
            ondelete="CASCADE",
            name="fk_academic_subject_result_eleve_school",
        ),
        sa.ForeignKeyConstraint(
            ["id_classe", "school_id"],
            ["classe.id", "classe.school_id"],
            ondelete="CASCADE",
            name="fk_academic_subject_result_classe_school",
        ),
        sa.ForeignKeyConstraint(
            ["id_matiere", "school_id"],
            ["matiere.id", "matiere.school_id"],
            ondelete="CASCADE",
            name="fk_academic_subject_result_matiere_school",
        ),
        sa.ForeignKeyConstraint(
            ["id_period", "school_id"],
            ["academic_period.id", "academic_period.school_id"],
            ondelete="CASCADE",
            name="fk_academic_subject_result_period_school",
        ),
        sa.ForeignKeyConstraint(
            ["ruleset_id", "school_id"],
            ["grading_ruleset.id", "grading_ruleset.school_id"],
            ondelete="SET NULL",
            name="fk_academic_subject_result_ruleset_school",
        ),
    )
    op.create_index("ix_academic_subject_result_school_id", "academic_subject_result", ["school_id"])
    op.create_index("ix_academic_subject_result_id_eleve", "academic_subject_result", ["id_eleve"])
    op.create_index("ix_academic_subject_result_id_classe", "academic_subject_result", ["id_classe"])
    op.create_index("ix_academic_subject_result_id_matiere", "academic_subject_result", ["id_matiere"])
    op.create_index("ix_academic_subject_result_id_period", "academic_subject_result", ["id_period"])
    op.create_index(
        "ix_academic_subject_result_stale",
        "academic_subject_result",
        ["school_id", "is_stale"],
    )

    op.add_column("bulletin", sa.Column("rulesets_snapshot", JSONB))
    op.add_column(
        "bulletin",
        sa.Column("results_calculated_at", sa.DateTime(timezone=True)),
    )

    after = {
        "notes": conn.execute(sa.text("SELECT COUNT(*) FROM note")).scalar(),
        "bulletins": conn.execute(sa.text("SELECT COUNT(*) FROM bulletin")).scalar(),
        "evaluations": conn.execute(sa.text("SELECT COUNT(*) FROM evaluation")).scalar(),
    }
    assert before == after, f"PR13 migration changed counts: {before} -> {after}"


def downgrade():
    op.drop_column("bulletin", "results_calculated_at")
    op.drop_column("bulletin", "rulesets_snapshot")
    op.drop_index("ix_academic_subject_result_stale", table_name="academic_subject_result")
    op.drop_index("ix_academic_subject_result_id_period", table_name="academic_subject_result")
    op.drop_index("ix_academic_subject_result_id_matiere", table_name="academic_subject_result")
    op.drop_index("ix_academic_subject_result_id_classe", table_name="academic_subject_result")
    op.drop_index("ix_academic_subject_result_id_eleve", table_name="academic_subject_result")
    op.drop_index("ix_academic_subject_result_school_id", table_name="academic_subject_result")
    op.drop_table("academic_subject_result")
