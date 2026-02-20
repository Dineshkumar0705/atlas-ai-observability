from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


# =====================================================
# BASE MODEL (Shared Fields)
# =====================================================

class TrustConfigBase(BaseModel):

    base_score: Optional[float] = Field(None, ge=0, le=200)

    hallucination_weight: Optional[float] = Field(None, ge=0)
    grounding_weight: Optional[float] = Field(None, ge=0)

    high_risk_penalty: Optional[float] = Field(None, ge=0)
    medium_risk_penalty: Optional[float] = Field(None, ge=0)
    critical_risk_penalty: Optional[float] = Field(None, ge=0)

    number_conflict_penalty: Optional[float] = Field(None, ge=0)
    confidence_mismatch_penalty: Optional[float] = Field(None, ge=0)
    semantic_risk_penalty: Optional[float] = Field(None, ge=0)

    @validator("*", pre=True)
    def prevent_negative_values(cls, v):
        if v is not None and v < 0:
            raise ValueError("Weight values cannot be negative")
        return v


# =====================================================
# UPDATE SCHEMA (PATCH)
# =====================================================

class TrustConfigUpdate(TrustConfigBase):
    """
    Partial update schema.
    Only provided fields will be modified.
    """
    pass


# =====================================================
# CREATE SCHEMA
# =====================================================

class TrustConfigCreate(TrustConfigBase):
    tenant_id: str = Field(..., min_length=2, max_length=100)
    environment: Optional[str] = Field("production")

    is_active: Optional[bool] = True


# =====================================================
# RESPONSE SCHEMA
# =====================================================

class TrustConfigResponse(BaseModel):

    tenant_id: str
    environment: str
    is_active: bool
    version: int

    base_score: float

    hallucination_weight: float
    grounding_weight: float

    high_risk_penalty: float
    medium_risk_penalty: float
    critical_risk_penalty: float

    number_conflict_penalty: float
    confidence_mismatch_penalty: float
    semantic_risk_penalty: float

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy ORM compatibility