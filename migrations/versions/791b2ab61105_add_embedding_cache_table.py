"""add embedding cache table

Revision ID: 791b2ab61105
Revises: 5bc57568e856
Create Date: 2026-02-18 12:18:54.236523
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision: str = "791b2ab61105"
down_revision: Union[str, Sequence[str], None] = "5bc57568e856"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create persistent embedding cache table.
    Multi-tenant safe.
    """

    op.create_table(
        "embedding_cache",

        # Primary key
        sa.Column("id", sa.Integer(), primary_key=True),

        # Tenant isolation
        sa.Column("tenant_id", sa.String(length=100), nullable=False),

        # Deterministic content hash
        sa.Column("content_hash", sa.String(length=64), nullable=False),

        # Optional raw text (can be trimmed later)
        sa.Column("original_text", sa.Text(), nullable=False),

        # Embedding vector (JSONB for flexibility)
        sa.Column(
            "embedding",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),

        sa.Column("model_used", sa.String(length=100), nullable=True),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.Column(
            "last_accessed",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.Column(
            "hit_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )

    # 🔐 Composite uniqueness (tenant safe)
    op.create_unique_constraint(
        "uq_embedding_cache_tenant_hash",
        "embedding_cache",
        ["tenant_id", "content_hash"],
    )

    # Performance indexes
    op.create_index(
        "ix_embedding_cache_tenant_id",
        "embedding_cache",
        ["tenant_id"],
    )

    op.create_index(
        "ix_embedding_cache_content_hash",
        "embedding_cache",
        ["content_hash"],
    )


def downgrade() -> None:
    """
    Drop embedding cache table.
    """

    op.drop_constraint(
        "uq_embedding_cache_tenant_hash",
        "embedding_cache",
        type_="unique",
    )

    op.drop_index(
        "ix_embedding_cache_content_hash",
        table_name="embedding_cache",
    )

    op.drop_index(
        "ix_embedding_cache_tenant_id",
        table_name="embedding_cache",
    )

    op.drop_table("embedding_cache")