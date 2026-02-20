from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Boolean,
    Index,
    UniqueConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base


class UsageMeter(Base):
    """
    Tracks monthly tenant usage for billing & analytics.

    Supports:
    - Request metering
    - Semantic usage tracking
    - Latency analytics
    - Overage calculation
    - Billing freeze snapshot
    """

    __tablename__ = "usage_meters"

    # ===================================================
    # PRIMARY KEY
    # ===================================================
    id = Column(Integer, primary_key=True, index=True)

    # ===================================================
    # TENANT + BILLING PERIOD
    # ===================================================
    tenant_id = Column(String(100), nullable=False, index=True)

    # Format: YYYY-MM (e.g., 2026-02)
    month = Column(String(7), nullable=False, index=True)

    # ===================================================
    # USAGE COUNTERS
    # ===================================================
    total_requests = Column(Integer, default=0, nullable=False)
    semantic_calls = Column(Integer, default=0, nullable=False)

    total_latency_ms = Column(Integer, default=0, nullable=False)

    # ===================================================
    # BILLING SNAPSHOT
    # ===================================================

    # Calculated live — but stored for reporting
    estimated_cost = Column(Numeric(12, 4), default=0, nullable=False)

    # Frozen cost once invoice generated
    final_billed_cost = Column(Numeric(12, 4), nullable=True)

    # True once month invoice is generated
    is_finalized = Column(Boolean, default=False)

    # ===================================================
    # METADATA
    # ===================================================
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # ===================================================
    # INDEXING FOR SCALE
    # ===================================================
    __table_args__ = (

        # Prevent duplicate meter rows
        UniqueConstraint(
            "tenant_id",
            "month",
            name="uq_tenant_month_usage"
        ),

        # Fast tenant-month queries
        Index("idx_tenant_month", "tenant_id", "month"),
    )