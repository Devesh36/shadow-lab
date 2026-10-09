from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("documents"):
        # Adopt only the exact baseline schema created by early local initialization.
        columns = {c["name"]: c for c in inspector.get_columns("documents")}
        expected = {"id": sa.String, "kind": sa.String, "parent_id": sa.String,
                    "data": sa.JSON, "created_at": sa.DateTime}
        if (set(columns) != set(expected) or any(not isinstance(columns[k]["type"], t) for k, t in expected.items())
                or inspector.get_pk_constraint("documents")["constrained_columns"] != ["id"]):
            raise RuntimeError("Existing documents schema does not match the ShadowLab baseline")
        indexes = {i["name"] for i in inspector.get_indexes("documents")}
        for field in ("kind", "parent_id"):
            if f"ix_documents_{field}" not in indexes:
                op.create_index(f"ix_documents_{field}", "documents", [field])
        return
    op.create_table("documents", sa.Column("id", sa.String(64), primary_key=True),
                    sa.Column("kind", sa.String(32), nullable=False),
                    sa.Column("parent_id", sa.String(64)), sa.Column("data", sa.JSON(), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_documents_kind", "documents", ["kind"])
    op.create_index("ix_documents_parent_id", "documents", ["parent_id"])


def downgrade():
    op.drop_table("documents")
