from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    Boolean,
    JSON,
    Index,
    UniqueConstraint,
    ForeignKey,
    Numeric
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class EvaluationLog(Base):
    """
    Enterprise-grade audit log for every ATLAS evaluation.

    Designed for:
    - Governance & compliance audits
    - Risk analytics
    - Multi-tenant SaaS scaling
    - Billing & metering
    - Replayable AI evaluation history
    - Forensic debugging
    """

    __tablename__ = "evaluation_logs"

    # ===================================================
    # PRIMARY KEY
    # ===================================================
    id = Column(Integer, primary_key=True, index=True)

    # ===================================================
    # TENANT & CONTEXT
    # ===================================================
    tenant_id = Column(
        String(100),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    tenant = relationship("Tenant")

    app_name = Column(String(100), nullable=False, index=True)
    environment = Column(String(50), default="production", index=True)

    # Optional reference to API key used
    api_key_id = Column(
        Integer,
        ForeignKey("tenant_api_keys.id", ondelete="SET NULL"),
        nullable=True
    )

    # Request classification
    request_type = Column(String(50), nullable=True)

    # ===================================================
    # MODEL METADATA
    # ===================================================
    model_provider = Column(String(100), nullable=True)
    model_name = Column(String(100), nullable=True)

    # ===================================================
    # CORE TRUST SCORES
    # ===================================================
    # ⚠ Changed to Float for precision
    trust_score = Column(Float, nullable=False, index=True)

    hallucination_probability = Column(Float, nullable=False)
    grounding_score = Column(Float, nullable=False)

    # ===================================================
    # BUSINESS RISK LAYER
    # ===================================================
    business_risk = Column(String(20), nullable=False, index=True)
    risk_score = Column(Integer, nullable=True)
    triggered_keywords = Column(JSON, nullable=True)

    # ===================================================
    # NUMERIC CONFLICT LAYER
    # ===================================================
    number_conflict = Column(Boolean, default=False)
    conflict_severity = Column(String(20), nullable=True)
    conflict_type = Column(String(50), nullable=True)

    # ===================================================
    # CONFIDENCE LAYER
    # ===================================================
    confidence_mismatch = Column(Boolean, default=False)

    # ===================================================
    # SEMANTIC VECTOR LAYER
    # ===================================================
    semantic_risk = Column(Boolean, default=False)
    semantic_similarity = Column(Float, nullable=True)
    semantic_model = Column(String(100), nullable=True)

    # ===================================================
    # FINAL DECISION
    # ===================================================
    recommendation = Column(String(20), nullable=False, index=True)

    # ===================================================
    # BILLING & METERING
    # ===================================================
    base_request_cost = Column(Numeric(10, 6), nullable=True)
    semantic_call_cost = Column(Numeric(10, 6), nullable=True)
    total_request_cost = Column(Numeric(10, 6), nullable=True)

    plan_name_snapshot = Column(String(50), nullable=True)
    plan_request_limit_snapshot = Column(Integer, nullable=True)

    # ===================================================
    # EXPLAINABILITY
    # ===================================================
    score_breakdown = Column(JSON, nullable=True)
    explanations = Column(JSON, nullable=True)

    # ===================================================
    # RAW INPUTS (Replayable AI Audit)
    # ===================================================
    user_query = Column(Text, nullable=False)
    retrieved_context = Column(JSON, nullable=True)
    llm_response = Column(Text, nullable=False)

    # ===================================================
    # SYSTEM METADATA
    # ===================================================
    atlas_version = Column(String(20), default="0.3.1")

    request_hash = Column(String(64), nullable=False)
    evaluation_latency_ms = Column(Integer, nullable=True)

    config_version = Column(Integer, nullable=True)

    # Soft delete support
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    # ===================================================
    # PERFORMANCE & ANALYTICS INDEXING
    # ===================================================
    __table_args__ = (

        # Per-app analytics
        Index("idx_app_created", "app_name", "created_at"),

        # Tenant + app drilldown
        Index("idx_tenant_app_date", "tenant_id", "app_name", "created_at"),

        # Risk analytics
        Index("idx_risk_recommendation", "business_risk", "recommendation"),

        # Trust trend
        Index("idx_trust_score_date", "trust_score", "created_at"),

        # Tenant billing queries
        Index("idx_tenant_created", "tenant_id", "created_at"),

        # Soft delete optimization
        Index("idx_tenant_active_logs", "tenant_id", "is_deleted"),

        # Deduplication safety
        UniqueConstraint(
            "request_hash",
            "tenant_id",
            name="uq_request_hash_tenant"
        ),
    )