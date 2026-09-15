"""PR #11 step 1 — Academic foundation : Program + AcademicPeriod + Level/Class program links.

Upgrade path (production-safe, UUID-preserving):
1. Create program + backfill GENERAL per school
2. Enrich trimestre → backfill school_id/sequence/code/label/period_type/program
3. Constraints on periods (drop numero IN 1..3)
4. niveau_etude.id_program + new uniqueness
5. classe.id_program aligned on niveau (composite FK)
6. Rename trimestre → academic_period

Downgrade: best-effort only while mono-program GENERAL and sequence<=3.
After multi-program adoption: FORWARD-ONLY (restore from backup).
"""

revision = "academic_foundation_pr11"
down_revision = "platform_super_admin"
branch_labels = None
depends_on = None


def upgrade():
    import sqlalchemy as sa
    from alembic import op
    from sqlalchemy.dialects.postgresql import UUID

    conn = op.get_bind()

    # --- BEFORE invariants (fail loudly if empty unexpected) ---
    before = {
        "schools": conn.execute(sa.text("SELECT COUNT(*) FROM schools")).scalar(),
        "annees": conn.execute(sa.text("SELECT COUNT(*) FROM annee_scolaire")).scalar(),
        "trimestres": conn.execute(sa.text("SELECT COUNT(*) FROM trimestre")).scalar(),
        "evaluations": conn.execute(sa.text("SELECT COUNT(*) FROM evaluation")).scalar(),
        "notes": conn.execute(sa.text("SELECT COUNT(*) FROM note")).scalar(),
        "bulletins": conn.execute(sa.text("SELECT COUNT(*) FROM bulletin")).scalar(),
        "inscriptions": conn.execute(sa.text("SELECT COUNT(*) FROM inscription")).scalar(),
    }
    uuid_map = {
        row.id: row.numero
        for row in conn.execute(sa.text("SELECT id, numero FROM trimestre")).fetchall()
    }

    # -------------------------------------------------------------------------
    # 1) Program
    # -------------------------------------------------------------------------
    op.create_table(
        "program",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("program_type", sa.String(40), nullable=False, server_default="general"),
        sa.Column("period_type_default", sa.String(20), nullable=False, server_default="trimestre"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("school_id", "code", name="uq_program_school_code"),
        sa.UniqueConstraint("id", "school_id", name="uq_program_id_school"),
    )
    op.create_index("ix_program_school_id", "program", ["school_id"])
    op.create_index("ix_program_school_active", "program", ["school_id", "is_active"])

    # 2) Backfill GENERAL (idempotent)
    conn.execute(
        sa.text(
            """
            INSERT INTO program (id, school_id, code, name, description, program_type, period_type_default, is_active)
            SELECT uuid_generate_v4(), s.id, 'GENERAL', 'Général',
                   'Programme de compatibilité historique (données pré-PR11).',
                   'general', 'trimestre', true
            FROM schools s
            WHERE NOT EXISTS (
                SELECT 1 FROM program p WHERE p.school_id = s.id AND p.code = 'GENERAL'
            )
            """
        )
    )

    # -------------------------------------------------------------------------
    # 3–5) Enrich trimestre → academic period fields
    # -------------------------------------------------------------------------
    op.add_column("trimestre", sa.Column("school_id", UUID(as_uuid=True), nullable=True))
    op.add_column("trimestre", sa.Column("id_program", UUID(as_uuid=True), nullable=True))
    op.add_column("trimestre", sa.Column("sequence", sa.SmallInteger(), nullable=True))
    op.add_column("trimestre", sa.Column("code", sa.String(20), nullable=True))
    op.add_column("trimestre", sa.Column("label", sa.String(80), nullable=True))
    op.add_column("trimestre", sa.Column("period_type", sa.String(20), nullable=True))
    op.add_column(
        "trimestre",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "trimestre",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.add_column(
        "trimestre",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    conn.execute(
        sa.text(
            """
            UPDATE trimestre t
            SET
                school_id = a.school_id,
                id_program = p.id,
                sequence = t.numero,
                code = 'T' || t.numero::text,
                label = 'Trimestre ' || t.numero::text,
                period_type = 'trimestre',
                is_active = true
            FROM annee_scolaire a
            JOIN program p ON p.school_id = a.school_id AND p.code = 'GENERAL'
            WHERE t.id_annee = a.id
            """
        )
    )

    orphan = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM trimestre WHERE school_id IS NULL OR id_program IS NULL OR sequence IS NULL"
        )
    ).scalar()
    if orphan:
        raise RuntimeError(f"Backfill academic_period incomplet : {orphan} lignes orphelines")

    # Drop legacy constraints on numero
    op.drop_constraint("trimestre_numero_check", "trimestre", type_="check")
    op.drop_constraint("trimestre_id_annee_numero_key", "trimestre", type_="unique")
    op.drop_constraint("trimestre_id_annee_fkey", "trimestre", type_="foreignkey")

    op.drop_column("trimestre", "numero")

    op.alter_column("trimestre", "school_id", nullable=False)
    op.alter_column("trimestre", "id_program", nullable=False)
    op.alter_column("trimestre", "sequence", nullable=False)
    op.alter_column("trimestre", "code", nullable=False)
    op.alter_column("trimestre", "label", nullable=False)
    op.alter_column("trimestre", "period_type", nullable=False)

    op.create_foreign_key(
        "fk_trimestre_school_id",
        "trimestre",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_academic_period_annee_school",
        "trimestre",
        "annee_scolaire",
        ["id_annee", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_academic_period_program_school",
        "trimestre",
        "program",
        ["id_program", "school_id"],
        ["id", "school_id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_academic_period_id_school", "trimestre", ["id", "school_id"])
    op.create_unique_constraint(
        "uq_academic_period_year_program_sequence",
        "trimestre",
        ["id_annee", "id_program", "sequence"],
    )
    op.create_unique_constraint(
        "uq_academic_period_year_program_code",
        "trimestre",
        ["id_annee", "id_program", "code"],
    )
    op.create_check_constraint(
        "ck_academic_period_sequence_positive",
        "trimestre",
        "sequence >= 1",
    )
    op.create_check_constraint(
        "ck_academic_period_dates",
        "trimestre",
        "date_fin >= date_debut",
    )
    op.create_check_constraint(
        "ck_academic_period_type",
        "trimestre",
        "period_type IN ('trimestre', 'semestre', 'custom', 'annuel')",
    )
    op.create_index("ix_academic_period_school_id", "trimestre", ["school_id"])
    op.create_index("ix_academic_period_year_program", "trimestre", ["id_annee", "id_program"])

    # -------------------------------------------------------------------------
    # 6–7) NiveauEtude.id_program
    # -------------------------------------------------------------------------
    op.add_column("niveau_etude", sa.Column("id_program", UUID(as_uuid=True), nullable=True))
    conn.execute(
        sa.text(
            """
            UPDATE niveau_etude n
            SET id_program = p.id
            FROM program p
            WHERE p.school_id = n.school_id AND p.code = 'GENERAL'
            """
        )
    )
    remaining_niveaux = conn.execute(
        sa.text("SELECT COUNT(*) FROM niveau_etude WHERE id_program IS NULL")
    ).scalar()
    if remaining_niveaux:
        raise RuntimeError(f"Backfill niveau_etude.id_program incomplet : {remaining_niveaux}")

    op.drop_constraint("uq_niveau_etude_school_libelle", "niveau_etude", type_="unique")
    op.alter_column("niveau_etude", "id_program", nullable=False)
    op.create_unique_constraint(
        "uq_niveau_etude_school_program_libelle",
        "niveau_etude",
        ["school_id", "id_program", "libelle"],
    )
    op.create_unique_constraint("uq_niveau_etude_id_program", "niveau_etude", ["id", "id_program"])
    op.create_foreign_key(
        "fk_niveau_etude_program_school",
        "niveau_etude",
        "program",
        ["id_program", "school_id"],
        ["id", "school_id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_niveau_etude_id_program", "niveau_etude", ["id_program"])

    # -------------------------------------------------------------------------
    # 8–9) Classe.id_program (aligné niveau)
    # -------------------------------------------------------------------------
    op.add_column("classe", sa.Column("id_program", UUID(as_uuid=True), nullable=True))
    conn.execute(
        sa.text(
            """
            UPDATE classe c
            SET id_program = n.id_program
            FROM niveau_etude n
            WHERE c.id_niveau = n.id
            """
        )
    )
    remaining_classes = conn.execute(
        sa.text("SELECT COUNT(*) FROM classe WHERE id_program IS NULL")
    ).scalar()
    if remaining_classes:
        raise RuntimeError(f"Backfill classe.id_program incomplet : {remaining_classes}")

    op.alter_column("classe", "id_program", nullable=False)
    op.create_foreign_key(
        "fk_classe_program_school",
        "classe",
        "program",
        ["id_program", "school_id"],
        ["id", "school_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_classe_niveau_program",
        "classe",
        "niveau_etude",
        ["id_niveau", "id_program"],
        ["id", "id_program"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_classe_id_program", "classe", ["id_program"])

    # -------------------------------------------------------------------------
    # 10) Rename trimestre → academic_period (FK enfants conservent les UUID)
    # -------------------------------------------------------------------------
    op.rename_table("trimestre", "academic_period")
    # Rename FK that still carries old name
    op.execute('ALTER TABLE academic_period RENAME CONSTRAINT fk_trimestre_school_id TO fk_academic_period_school_id')

    # --- AFTER invariants ---
    after = {
        "schools": conn.execute(sa.text("SELECT COUNT(*) FROM schools")).scalar(),
        "annees": conn.execute(sa.text("SELECT COUNT(*) FROM annee_scolaire")).scalar(),
        "trimestres": conn.execute(sa.text("SELECT COUNT(*) FROM academic_period")).scalar(),
        "evaluations": conn.execute(sa.text("SELECT COUNT(*) FROM evaluation")).scalar(),
        "notes": conn.execute(sa.text("SELECT COUNT(*) FROM note")).scalar(),
        "bulletins": conn.execute(sa.text("SELECT COUNT(*) FROM bulletin")).scalar(),
        "inscriptions": conn.execute(sa.text("SELECT COUNT(*) FROM inscription")).scalar(),
    }
    for key, value in before.items():
        if after[key] != value:
            raise RuntimeError(f"Invariant BEFORE/AFTER cassé pour {key}: {value} → {after[key]}")

    after_ids = {
        row.id: row.sequence
        for row in conn.execute(sa.text("SELECT id, sequence FROM academic_period")).fetchall()
    }
    if set(after_ids.keys()) != set(uuid_map.keys()):
        raise RuntimeError("UUID academic_period ≠ UUID trimestre historiques")
    for pid, numero in uuid_map.items():
        if after_ids[pid] != numero:
            raise RuntimeError(f"sequence ≠ numero pour période {pid}")


def downgrade():
    """Best-effort mono-program only. Unsafe after multi-program adoption."""
    import sqlalchemy as sa
    from alembic import op
    from sqlalchemy.dialects.postgresql import UUID

    conn = op.get_bind()

    multi = conn.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM (
                SELECT school_id FROM program GROUP BY school_id HAVING COUNT(*) > 1
            ) x
            """
        )
    ).scalar()
    if multi:
        raise RuntimeError(
            "Downgrade refusé : des écoles ont plusieurs programs (FORWARD-ONLY). "
            "Restaurer depuis backup."
        )

    high_seq = conn.execute(
        sa.text("SELECT COUNT(*) FROM academic_period WHERE sequence > 3")
    ).scalar()
    if high_seq:
        raise RuntimeError("Downgrade refusé : des périodes ont sequence > 3 (FORWARD-ONLY).")

    op.rename_table("academic_period", "trimestre")
    op.execute(
        'ALTER TABLE trimestre RENAME CONSTRAINT fk_academic_period_school_id TO fk_trimestre_school_id'
    )

    op.drop_constraint("fk_classe_niveau_program", "classe", type_="foreignkey")
    op.drop_constraint("fk_classe_program_school", "classe", type_="foreignkey")
    op.drop_index("ix_classe_id_program", table_name="classe")
    op.drop_column("classe", "id_program")

    op.drop_constraint("fk_niveau_etude_program_school", "niveau_etude", type_="foreignkey")
    op.drop_constraint("uq_niveau_etude_id_program", "niveau_etude", type_="unique")
    op.drop_constraint("uq_niveau_etude_school_program_libelle", "niveau_etude", type_="unique")
    op.drop_index("ix_niveau_etude_id_program", table_name="niveau_etude")
    op.drop_column("niveau_etude", "id_program")
    op.create_unique_constraint(
        "uq_niveau_etude_school_libelle", "niveau_etude", ["school_id", "libelle"]
    )

    op.drop_index("ix_academic_period_year_program", table_name="trimestre")
    op.drop_index("ix_academic_period_school_id", table_name="trimestre")
    op.drop_constraint("ck_academic_period_type", "trimestre", type_="check")
    op.drop_constraint("ck_academic_period_dates", "trimestre", type_="check")
    op.drop_constraint("ck_academic_period_sequence_positive", "trimestre", type_="check")
    op.drop_constraint("uq_academic_period_year_program_code", "trimestre", type_="unique")
    op.drop_constraint("uq_academic_period_year_program_sequence", "trimestre", type_="unique")
    op.drop_constraint("uq_academic_period_id_school", "trimestre", type_="unique")
    op.drop_constraint("fk_academic_period_program_school", "trimestre", type_="foreignkey")
    op.drop_constraint("fk_academic_period_annee_school", "trimestre", type_="foreignkey")
    op.drop_constraint("fk_trimestre_school_id", "trimestre", type_="foreignkey")

    op.add_column("trimestre", sa.Column("numero", sa.SmallInteger(), nullable=True))
    conn.execute(sa.text("UPDATE trimestre SET numero = sequence"))
    op.alter_column("trimestre", "numero", nullable=False)
    op.create_check_constraint("trimestre_numero_check", "trimestre", "numero IN (1, 2, 3)")
    op.create_unique_constraint("trimestre_id_annee_numero_key", "trimestre", ["id_annee", "numero"])
    op.create_foreign_key(
        "trimestre_id_annee_fkey",
        "trimestre",
        "annee_scolaire",
        ["id_annee"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_column("trimestre", "updated_at")
    op.drop_column("trimestre", "created_at")
    op.drop_column("trimestre", "is_active")
    op.drop_column("trimestre", "period_type")
    op.drop_column("trimestre", "label")
    op.drop_column("trimestre", "code")
    op.drop_column("trimestre", "sequence")
    op.drop_column("trimestre", "id_program")
    op.drop_column("trimestre", "school_id")

    op.drop_index("ix_program_school_active", table_name="program")
    op.drop_index("ix_program_school_id", table_name="program")
    op.drop_table("program")
