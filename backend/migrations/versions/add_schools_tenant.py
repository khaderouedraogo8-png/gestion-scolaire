"""Phase 1 multi-tenant : table schools + utilisateur.school_id + école par défaut."""
revision = "add_schools_tenant"
down_revision = "add_pedagogie_extensions"
branch_labels = None
depends_on = None

DEFAULT_SCHOOL_CODE = "ECOLE-EXISTANTE"


def upgrade():
    from alembic import op
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import UUID

    op.create_table(
        "schools",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=150)),
        sa.Column("phone", sa.String(length=30)),
        sa.Column("address", sa.Text()),
        sa.Column("city", sa.String(length=80)),
        sa.Column("country", sa.String(length=80)),
        sa.Column("logo", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_schools_code"),
    )

    op.add_column("utilisateur", sa.Column("school_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_utilisateur_school_id",
        "utilisateur",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_utilisateur_school_id", "utilisateur", ["school_id"], unique=False)

    conn = op.get_bind()

    # École de migration : réutiliser le nom d'établissement s'il existe
    etab = conn.execute(
        sa.text("SELECT nom, email, telephone, adresse, ville, pays, logo_url FROM etablissement LIMIT 1")
    ).mappings().first()

    if etab:
        name = etab["nom"] or "École existante"
        email = etab["email"]
        phone = etab["telephone"]
        address = etab["adresse"]
        city = etab["ville"]
        country = etab["pays"]
        logo = etab["logo_url"]
    else:
        name = "École existante"
        email = phone = address = city = country = logo = None

    existing = conn.execute(
        sa.text("SELECT id FROM schools WHERE code = :code"),
        {"code": DEFAULT_SCHOOL_CODE},
    ).first()

    if existing:
        school_id = existing[0]
    else:
        school_id = conn.execute(
            sa.text(
                """
                INSERT INTO schools (id, name, code, email, phone, address, city, country, logo, is_active)
                VALUES (uuid_generate_v4(), :name, :code, :email, :phone, :address, :city, :country, :logo, true)
                RETURNING id
                """
            ),
            {
                "name": name,
                "code": DEFAULT_SCHOOL_CODE,
                "email": email,
                "phone": phone,
                "address": address,
                "city": city,
                "country": country,
                "logo": logo,
            },
        ).scalar_one()

    conn.execute(
        sa.text(
            """
            UPDATE utilisateur
            SET school_id = :school_id
            WHERE school_id IS NULL
            """
        ),
        {"school_id": school_id},
    )


def downgrade():
    from alembic import op

    op.drop_index("ix_utilisateur_school_id", table_name="utilisateur")
    op.drop_constraint("fk_utilisateur_school_id", "utilisateur", type_="foreignkey")
    op.drop_column("utilisateur", "school_id")
    op.drop_table("schools")
