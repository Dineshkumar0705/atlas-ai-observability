from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Tenant(Base):
    """
    SaaS Tenant Model for ATLAS.

    Supports:
    - Multi-tenant isolation
    - Subscription lifecycle
    - Plan-based enforcement
    - Usage tracking
    - Billing readiness
    """

    __tablename__ = "tenants"

    # ===================================================
    # PRIMARY KEY
    # ===================================================
    id = Column(Integer, primary_key=True, index=True)

    # ===================================================
    # PUBLIC IDENTIFIER (Used in API)
    # ===================================================
    tenant_id = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    # ===================================================
    # BUSINESS METADATA
    # ===================================================
    name = Column(String(150), nullable=False)
    owner_email = Column(String(150), nullable=True)

    # ===================================================
    # PLAN RELATIONSHIP
    # ===================================================
    pricing_plan_id = Column(
        Integer,
        ForeignKey("pricing_plans.id", ondelete="RESTRICT"),
        nullable=False
    )

    pricing_plan = relationship(
        "PricingPlan",
        back_populates="tenants",
        lazy="joined"
    )

    # ===================================================
    # USAGE TRACKING
    # ===================================================
    current_month_usage = Column(
        Integer,
        nullable=False,
        default=0
    )

    lifetime_usage = Column(
        Integer,
        nullable=False,
        default=0
    )

    current_month_overage = Column(
        Integer,
        nullable=False,
        default=0
    )

    current_month_cost = Column(
        Numeric(10, 2),
        nullable=False,
        default=0.00
    )

    # ===================================================
    # BILLING CYCLE WINDOW
    # ===================================================
    billing_cycle_start = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    billing_cycle_end = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # ===================================================
    # SUBSCRIPTION STATUS
    # ===================================================
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )

    is_suspended = Column(
        Boolean,
        nullable=False,
        default=False
    )

    is_trial = Column(
        Boolean,
        nullable=False,
        default=False
    )

    trial_ends_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # ===================================================
    # API RATE ENFORCEMENT
    # ===================================================
    last_request_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # ===================================================
    # SYSTEM METADATA
    # ===================================================
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # ===================================================
    # COMPOSITE INDEXES (ENTERPRISE SAFE NAMING)
    # ===================================================
    __table_args__ = (

        # 🔥 Renamed — globally unique
        Index(
            "idx_tenants_tenant_active",
            "tenant_id",
            "is_active"
        ),

        Index(
            "idx_tenants_plan_active",
            "pricing_plan_id",
            "is_active"
        ),
    )