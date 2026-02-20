from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    Boolean,
    Index,
    UniqueConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base


class TrustConfig(Base):
    """
    Per-tenant Trust Weight Configuration.

    Enables:
    - SaaS multi-tenant isolation
    - Runtime weight tuning
    - A/B experimentation
    - Governance flexibility
    """

    __tablename__ = "trust_configs"

    # --------------------------------------------------
    # Primary Key
    # --------------------------------------------------
    id = Column(Integer, primary_key=True, index=True)

    # --------------------------------------------------
    # Tenant Isolation
    # --------------------------------------------------
    tenant_id = Column(String(100), nullable=False)

    # Optional environment separation (prod/staging/dev)
    environment = Column(String(50), nullable=False, default="production")

    # Active toggle (feature flag control)
    is_active = Column(Boolean, nullable=False, default=True)

    # --------------------------------------------------
    # Core Scoring Parameters
    # --------------------------------------------------
    base_score = Column(Float, nullable=False, default=100.0)

    hallucination_weight = Column(Float, nullable=False, default=50.0)
    grounding_weight = Column(Float, nullable=False, default=30.0)

    # --------------------------------------------------
    # Risk Penalties
    # --------------------------------------------------
    high_risk_penalty = Column(Float, nullable=False, default=15.0)
    medium_risk_penalty = Column(Float, nullable=False, default=8.0)
    critical_risk_penalty = Column(Float, nullable=False, default=25.0)

    # --------------------------------------------------
    # Behavioral Penalties
    # --------------------------------------------------
    number_conflict_penalty = Column(Float, nullable=False, default=15.0)
    confidence_mismatch_penalty = Column(Float, nullable=False, default=12.0)
    semantic_risk_penalty = Column(Float, nullable=False, default=15.0)

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------
    version = Column(Integer, nullable=False, default=1)

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

    # --------------------------------------------------
    # Constraints & Indexing
    # --------------------------------------------------
    __table_args__ = (

        # Prevent duplicate config per tenant+environment
        UniqueConstraint(
            "tenant_id",
            "environment",
            name="uq_trust_configs_tenant_environment"
        ),

        # 🔥 RENAMED — now globally unique
        Index(
            "idx_trust_configs_tenant_active",
            "tenant_id",
            "is_active"
        ),
    )