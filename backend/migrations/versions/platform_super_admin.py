"""PR #10 — super_admin plateforme + school_id nullable conditionnel + audit hybride."""

revision = "platform_super_admin"
down_revision = "tenant_school_id_not_null"
branch_labels = None
depends_on = None


def upgrade():
    import sqlalchemy as sa
    from alembic import op
    from sqlalchemy.dialects.postgresql import UUID

    # 1) utilisateurs.school_id : autoriser NULL pour super_admin uniquement
    op.alter_column(
        "utilisateur",
        "school_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_utilisateur_super_admin_school",
        "utilisateur",
        "(role = 'super_admin' AND school_id IS NULL) OR "
        "(role <> 'super_admin' AND school_id IS NOT NULL)",
    )

    # Étendre le CHECK métier des rôles (héritage schema SQL initial)
    op.drop_constraint("utilisateur_role_check", "utilisateur", type_="check")
    op.create_check_constraint(
        "utilisateur_role_check",
        "utilisateur",
        "role IN ("
        "'administrateur', 'directeur', 'enseignant', 'agent_comptable', "
        "'secretariat', 'parent', 'super_admin')",
    )

    # 2) schools.created_by (onboarding audit)
    op.add_column(
        "schools",
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_schools_created_by_utilisateur",
        "schools",
        "utilisateur",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_schools_created_by", "schools", ["created_by"])

    # 3) journal_audit.school_id nullable (événements plateforme)
    op.alter_column(
        "journal_audit",
        "school_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )


def downgrade():
    import sqlalchemy as sa
    from alembic import op
    from sqlalchemy.dialects.postgresql import UUID

    conn = op.get_bind()

    # Bloquer le downgrade s'il reste des super_admin / school_id NULL
    remaining_super = conn.execute(
        sa.text("SELECT COUNT(*) FROM utilisateur WHERE role = 'super_admin' OR school_id IS NULL")
    ).scalar()
    if remaining_super and int(remaining_super) > 0:
        raise RuntimeError(
            "Downgrade impossible : des utilisateurs super_admin ou school_id NULL existent. "
            "Supprimez-les ou réassignez-les avant downgrade."
        )

    remaining_audit = conn.execute(
        sa.text("SELECT COUNT(*) FROM journal_audit WHERE school_id IS NULL")
    ).scalar()
    if remaining_audit and int(remaining_audit) > 0:
        raise RuntimeError(
            "Downgrade impossible : des entrées journal_audit.school_id NULL existent."
        )

    op.alter_column(
        "journal_audit",
        "school_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )

    op.drop_index("ix_schools_created_by", table_name="schools")
    op.drop_constraint("fk_schools_created_by_utilisateur", "schools", type_="foreignkey")
    op.drop_column("schools", "created_by")

    op.drop_constraint("ck_utilisateur_super_admin_school", "utilisateur", type_="check")
    op.drop_constraint("utilisateur_role_check", "utilisateur", type_="check")
    op.create_check_constraint(
        "utilisateur_role_check",
        "utilisateur",
        "role IN ("
        "'administrateur', 'directeur', 'enseignant', 'agent_comptable', "
        "'secretariat', 'parent')",
    )
    op.alter_column(
        "utilisateur",
        "school_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )
