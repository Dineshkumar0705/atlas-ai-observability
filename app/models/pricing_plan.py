from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Numeric,
    DateTime,
    JSON,
    Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PricingPlan(Base):
    """
    SaaS Pricing Plan Model for ATLAS.

    Supports:
    - Tier-based pricing (FREE / PRO / ENTERPRISE)
    - Hard & soft limits
    - Overage billing
    - Semantic usage billing
    - Feature flag control
    - Rate limiting configuration
    """

    __tablename__ = "pricing_plans"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------
    id = Column(Integer, primary_key=True, index=True)

    # ---------------------------------------------------
    # Plan Identity
    # ---------------------------------------------------
    name = Column(String(50), nullable=False, unique=True, index=True)
    tier = Column(String(30), nullable=False, index=True)  # FREE / PRO / ENTERPRISE
    description = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # ---------------------------------------------------
    # Pricing (Precise Money Handling)
    # ---------------------------------------------------
    monthly_price = Column(
        Numeric(10, 2),
        nullable=False
    )

    overage_per_request = Column(
        Numeric(10, 6),
        nullable=False,
        default=0.001
    )

    semantic_call_cost = Column(
        Numeric(10, 6),
        nullable=False,
        default=0.0005
    )

    # ---------------------------------------------------
    # Usage Limits
    # ---------------------------------------------------
    request_limit = Column(Integer, nullable=False)

    # If True → Block after limit
    hard_limit = Column(Boolean, default=True, nullable=False)

    # Per-minute rate limit
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)

    # ---------------------------------------------------
    # Feature Flags
    # IMPORTANT: Never use mutable dict directly as default
    # ---------------------------------------------------
    features = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "semantic_enabled": True,
            "confidence_layer_enabled": True,
            "advanced_analytics": False,
            "priority_support": False,
        }
    )

    # ---------------------------------------------------
    # Versioning
    # ---------------------------------------------------
    version = Column(Integer, default=1, nullable=False)

    # ---------------------------------------------------
    # Reverse Relationship (Fixes your earlier crash)
    # ---------------------------------------------------
    tenants = relationship(
        "Tenant",
        back_populates="pricing_plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # ---------------------------------------------------
    # Audit
    # ---------------------------------------------------
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # ---------------------------------------------------
    # Performance Indexes
    # ---------------------------------------------------
    __table_args__ = (
        Index("idx_plan_tier_active", "tier", "is_active"),
        Index("idx_plan_price_active", "monthly_price", "is_active"),
    )