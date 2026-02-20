from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Index
)
from sqlalchemy.sql import func
from app.core.database import Base


class TenantAPIKey(Base):
    """
    API key model for authenticating tenant requests.

    Designed for:
    - Secure API access
    - Key rotation
    - Environment separation
    - Rate limiting
    - Usage analytics
    """

    __tablename__ = "tenant_api_keys"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------
    id = Column(Integer, primary_key=True, index=True)

    # ---------------------------------------------------
    # Tenant Association
    # ---------------------------------------------------
    tenant_id = Column(
        String(100),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ---------------------------------------------------
    # API Key Details
    # ---------------------------------------------------
    api_key_hash = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True
    )

    key_prefix = Column(
        String(20),
        nullable=True,
        index=True
    )
    # Example: sk_live, sk_test

    environment = Column(
        String(50),
        default="production",
        index=True
    )

    # ---------------------------------------------------
    # Status
    # ---------------------------------------------------
    is_active = Column(Boolean, default=True, index=True)
    is_revoked = Column(Boolean, default=False)

    # ---------------------------------------------------
    # Usage & Limits
    # ---------------------------------------------------
    usage_count = Column(Integer, default=0)
    rate_limit_per_minute = Column(Integer, default=60)

    # ---------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ---------------------------------------------------
    # Composite Indexes
    # ---------------------------------------------------
    __table_args__ = (
        Index("idx_tenant_env", "tenant_id", "environment"),
        Index("idx_key_status", "tenant_id", "is_active"),
    )