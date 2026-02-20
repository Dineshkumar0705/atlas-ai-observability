from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


# =====================================================
# ENUMS (Stronger API Contracts)
# =====================================================

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Recommendation(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"


# =====================================================
# MODEL INFO STRUCTURE
# =====================================================

class ModelInfo(BaseModel):
    provider: Optional[str] = Field(
        default=None,
        example="openai"
    )
    model: Optional[str] = Field(
        default=None,
        example="gpt-4"
    )


# =====================================================
# REQUEST SCHEMA
# =====================================================

class AtlasRequest(BaseModel):
    app_name: str = Field(..., example="support-bot")

    user_query: str = Field(
        ...,
        example="Can I get a refund after 90 days?"
    )

    retrieved_context: List[str] = Field(
        ...,
        example=["Refunds are allowed within 30 days."]
    )

    llm_response: str = Field(
        ...,
        example="Yes, refunds are allowed up to 120 days."
    )

    model_info: Optional[ModelInfo] = Field(
        default=None
    )

    tenant_id: Optional[str] = Field(
        default=None,
        description="Optional multi-tenant identifier"
    )


# =====================================================
# RESPONSE SCHEMA
# =====================================================

class AtlasResponse(BaseModel):
    trust_score: int = Field(..., ge=0, le=100)
    hallucination_probability: float = Field(..., ge=0.0, le=1.0)
    grounding_score: float = Field(..., ge=0.0, le=1.0)

    business_risk: RiskLevel
    recommendation: Recommendation

    number_conflict: Optional[bool] = Field(
        default=False,
        description="Indicates numeric contradiction detected"
    )

    confidence_mismatch: Optional[bool] = Field(
        default=False,
        description="True if response tone is overly confident with weak grounding"
    )

    explanations: Optional[List[str]] = Field(
        default_factory=list,
        description="Human-readable reasoning signals"
    )

    evaluated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow
    )


# =====================================================
# ANALYTICS SCHEMAS
# =====================================================

class StatsSummary(BaseModel):
    total_requests: int
    avg_trust_score: Optional[float]
    block_rate: Optional[float]
    high_risk_rate: Optional[float]


class StatsResponse(BaseModel):
    app_name: Optional[str]
    summary: StatsSummary
    generated_at: datetime


# =====================================================
# WEIGHT TUNING SCHEMAS (Next Phase Ready)
# =====================================================

class WeightConfig(BaseModel):
    hallucination_weight: float = Field(default=50.0)
    grounding_weight: float = Field(default=30.0)
    high_risk_penalty: float = Field(default=10.0)
    number_conflict_penalty: float = Field(default=15.0)
    confidence_mismatch_penalty: float = Field(default=10.0)
    semantic_risk_penalty: float = Field(default=15.0)


class WeightUpdateResponse(BaseModel):
    message: str
    updated_config: WeightConfig
    updated_at: datetime