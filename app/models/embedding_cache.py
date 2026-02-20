from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class EmbeddingCache(Base):
    """
    Persistent embedding cache.

    Stores embeddings per tenant.
    Used for semantic grounding reuse.
    """

    __tablename__ = "embedding_cache"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(String, index=True, nullable=True)

    # SHA256 hash of input text
    content_hash = Column(String(64), unique=True, index=True, nullable=False)

    # Original text (optional but useful for debugging)
    original_text = Column(Text, nullable=False)

    # Store embedding as JSON array
    embedding = Column(JSONB, nullable=False)

    # Metadata
    model_used = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed = Column(DateTime(timezone=True), server_default=func.now())

    hit_count = Column(Integer, default=0)