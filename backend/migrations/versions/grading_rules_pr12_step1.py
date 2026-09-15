"""PR #12 step 1 — Grading rules engine foundation (DB models only).

Creates:
- evaluation_type (per-school controlled catalog, system seed)
- grading_ruleset (versioned rules, scoped School×Year×Program?×Level?×Subject?)
- grading_rule_component (percent weights; type ≠ context)

Non-destructive: does not alter evaluation/note/bulletin/coefficient_matiere.
No backfill of legacy formulas (old flat average remains until later steps).
"""

revision = "grading_rules_pr12_step1"
down_revision = "academic_foundation_pr11"
branch_labels = None
depends_on = None

SYSTEM_EVALUATION_TYPES = (
    ("devoir", "Devoir"),
    ("interrogation", "Interrogation"),
    ("composition", "Composition"),
    ("examen", "Examen"),
    ("tp", "Travaux pratiques"),
    ("oral", "Oral"),
    ("projet", "Projet"),
    ("exam_blanc", "Examen blanc"),
    ("rattrapage", "Rattrapage"),
)


def upgrade():
    import sqlalchemy as sa
    from alembic import op
    from sqlalchemy.dialects.postgresql import UUID

    conn = op.get_bind()

    before = {
        "schools": conn.execute(sa.text("SELECT COUNT(*) FROM schools")).scalar(),
        "evaluations": conn.execute(sa.text("SELECT COUNT(*) FROM evaluation")).scalar(),
        "notes": conn.execute(sa.text("SELECT COUNT(*) FROM note")).scalar(),
        "bulletins": conn.execute(sa.text("SELECT COUNT(*) FROM bulletin")).scalar(),
        "coefficient_matiere": conn.execute(sa.text("SELECT COUNT(*) FROM coefficient_matiere")).scalar(),
    }

    # -------------------------------------------------------------------------
    # 1) evaluation_type
    # -------------------------------------------------------------------------
    op.create_table(
        "evaluation_type",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column(
            "school_id",
            UUID(as_uuid=True),
            sa.ForeignKey("schools.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("school_id", "code", name="uq_evaluation_type_school_code"),
        sa.UniqueConstraint("id", "school_id", name="uq_evaluation_type_id_school"),
    )
    op.create_index("ix_evaluation_type_school_id", "evaluation_type", ["school_id"])
    op.create_index(
        "ix_evaluation_type_school_active",
        "evaluation_type",
        ["school_id", "is_active"],
    )

    # Seed system catalog per school (idempotent)
    for code, label in SYSTEM_EVALUATION_TYPES:
        conn.execute(
            sa.text(
                """
                INSERT INTO evaluation_type (id, school_id, code, label, is_system, is_active)
                SELECT uuid_generate_v4(), s.id, :code, :label, true, true
                FROM schools s
                WHERE NOT EXISTS (
                    SELECT 1 FROM evaluation_type et
                    WHERE et.school_id = s.id AND et.code = :code
                )
                """
            ),
            {"code": code, "label": label},
        )

    # -------------------------------------------------------------------------
    # 2) grading_ruleset
    # -------------------------------------------------------------------------
    op.create_table(
        "grading_ruleset",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column(
            "school_id",
            UUID(as_uuid=True),
            sa.ForeignKey("schools.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id_annee", UUID(as_uuid=True), nullable=False),
        sa.Column("id_program", UUID(as_uuid=True), nullable=True),
        sa.Column("id_niveau", UUID(as_uuid=True), nullable=True),
        sa.Column("id_matiere", UUID(as_uuid=True), nullable=True),
        sa.Column("scale_max", sa.Numeric(6, 2), nullable=False, server_default="20.00"),
        sa.Column("rounding_mode", sa.String(20), nullable=False, server_default="half_up"),
        sa.Column("rounding_precision", sa.SmallInteger(), nullable=False, server_default="2"),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("utilisateur.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("school_id", "code", "version", name="uq_grading_ruleset_school_code_version"),
        sa.UniqueConstraint("id", "school_id", name="uq_grading_ruleset_id_school"),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_grading_ruleset_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_grading_ruleset_version_positive"),
        sa.CheckConstraint("scale_max > 0", name="ck_grading_ruleset_scale_max_positive"),
        sa.CheckConstraint("rounding_precision >= 0", name="ck_grading_ruleset_rounding_precision"),
        sa.CheckConstraint(
            "rounding_mode IN ('half_up', 'half_even', 'down', 'up')",
            name="ck_grading_ruleset_rounding_mode",
        ),
        sa.CheckConstraint(
            "(id_niveau IS NULL) OR (id_program IS NOT NULL)",
            name="ck_grading_ruleset_niveau_requires_program",
        ),
        sa.ForeignKeyConstraint(
            ["id_annee", "school_id"],
            ["annee_scolaire.id", "annee_scolaire.school_id"],
            ondelete="RESTRICT",
            name="fk_grading_ruleset_annee_school",
        ),
        sa.ForeignKeyConstraint(
            ["id_program", "school_id"],
            ["program.id", "program.school_id"],
            ondelete="RESTRICT",
            name="fk_grading_ruleset_program_school",
        ),
        sa.ForeignKeyConstraint(
            ["id_niveau", "school_id"],
            ["niveau_etude.id", "niveau_etude.school_id"],
            ondelete="RESTRICT",
            name="fk_grading_ruleset_niveau_school",
        ),
        sa.ForeignKeyConstraint(
            ["id_matiere", "school_id"],
            ["matiere.id", "matiere.school_id"],
            ondelete="RESTRICT",
            name="fk_grading_ruleset_matiere_school",
        ),
    )
    op.create_index("ix_grading_ruleset_school_id", "grading_ruleset", ["school_id"])
    # Résolution future : school + year + status (+ axes optionnels)
    op.create_index(
        "ix_grading_ruleset_resolve",
        "grading_ruleset",
        ["school_id", "id_annee", "status", "id_program", "id_niveau", "id_matiere"],
    )
    op.create_index(
        "ix_grading_ruleset_school_code_status",
        "grading_ruleset",
        ["school_id", "code", "status"],
    )

    # -------------------------------------------------------------------------
    # 3) grading_rule_component
    # -------------------------------------------------------------------------
    op.create_table(
        "grading_rule_component",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column(
            "school_id",
            UUID(as_uuid=True),
            sa.ForeignKey("schools.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("ruleset_id", UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("id_evaluation_type", UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_context", sa.String(40), nullable=False, server_default="normal"),
        sa.Column("weight", sa.Numeric(5, 2), nullable=False),
        sa.Column("sequence", sa.SmallInteger(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("ruleset_id", "code", name="uq_grading_rule_component_ruleset_code"),
        sa.UniqueConstraint("ruleset_id", "sequence", name="uq_grading_rule_component_ruleset_sequence"),
        sa.UniqueConstraint("id", "school_id", name="uq_grading_rule_component_id_school"),
        sa.CheckConstraint("weight > 0 AND weight <= 100", name="ck_grading_rule_component_weight"),
        sa.CheckConstraint("sequence >= 1", name="ck_grading_rule_component_sequence"),
        sa.CheckConstraint(
            "evaluation_context IN ('normal', 'examen_blanc', 'rattrapage', 'session_2')",
            name="ck_grading_rule_component_context",
        ),
        sa.ForeignKeyConstraint(
            ["ruleset_id", "school_id"],
            ["grading_ruleset.id", "grading_ruleset.school_id"],
            ondelete="CASCADE",
            name="fk_grading_rule_component_ruleset_school",
        ),
        sa.ForeignKeyConstraint(
            ["id_evaluation_type", "school_id"],
            ["evaluation_type.id", "evaluation_type.school_id"],
            ondelete="RESTRICT",
            name="fk_grading_rule_component_eval_type_school",
        ),
    )
    op.create_index("ix_grading_rule_component_school_id", "grading_rule_component", ["school_id"])
    op.create_index("ix_grading_rule_component_ruleset_id", "grading_rule_component", ["ruleset_id"])
    op.create_index(
        "ix_grading_rule_component_ruleset_seq",
        "grading_rule_component",
        ["ruleset_id", "sequence"],
    )

    after = {
        "schools": conn.execute(sa.text("SELECT COUNT(*) FROM schools")).scalar(),
        "evaluations": conn.execute(sa.text("SELECT COUNT(*) FROM evaluation")).scalar(),
        "notes": conn.execute(sa.text("SELECT COUNT(*) FROM note")).scalar(),
        "bulletins": conn.execute(sa.text("SELECT COUNT(*) FROM bulletin")).scalar(),
        "coefficient_matiere": conn.execute(sa.text("SELECT COUNT(*) FROM coefficient_matiere")).scalar(),
    }
    if before != after:
        raise RuntimeError(f"Données métier altérées par migration grading: {before=} {after=}")


def downgrade():
    from alembic import op

    op.drop_index("ix_grading_rule_component_ruleset_seq", table_name="grading_rule_component")
    op.drop_index("ix_grading_rule_component_ruleset_id", table_name="grading_rule_component")
    op.drop_index("ix_grading_rule_component_school_id", table_name="grading_rule_component")
    op.drop_table("grading_rule_component")

    op.drop_index("ix_grading_ruleset_school_code_status", table_name="grading_ruleset")
    op.drop_index("ix_grading_ruleset_resolve", table_name="grading_ruleset")
    op.drop_index("ix_grading_ruleset_school_id", table_name="grading_ruleset")
    op.drop_table("grading_ruleset")

    op.drop_index("ix_evaluation_type_school_active", table_name="evaluation_type")
    op.drop_index("ix_evaluation_type_school_id", table_name="evaluation_type")
    op.drop_table("evaluation_type")
