from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
import time

from app.core.database import get_db
from app.core.security import get_current_tenant
from app.models.tenant import Tenant


router = APIRouter(
    prefix="/v1",
    tags=["Evaluation"]
)


# ============================================================
# REQUEST MODEL
# ============================================================

class EvaluationRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    app_name: str = Field(default="default_app")
    environment: str = Field(default="production")


# ============================================================
# RESPONSE MODEL
# ============================================================

class EvaluationResponse(BaseModel):
    request_id: str
    tenant_id: str
    message: str
    trust_score: float
    latency_ms: int
    timestamp: datetime


# ============================================================
# MAIN EVALUATION ENDPOINT
# ============================================================

@router.post(
    "/evaluate",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK
)
def evaluate(
    payload: EvaluationRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Main ATLAS Evaluation Entry Point.

    Responsibilities:
    - Authenticates tenant
    - Validates plan status
    - Tracks usage
    - Routes to Trust Engine (future)
    """

    start_time = time.time()

    # --------------------------------------------------------
    # Subscription Guard
    # --------------------------------------------------------
    if not tenant.is_active or tenant.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account inactive or suspended."
        )

    # --------------------------------------------------------
    # Usage Enforcement (basic hook)
    # --------------------------------------------------------
    if tenant.pricing_plan.hard_limit:
        if tenant.current_month_usage >= tenant.pricing_plan.request_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Monthly request limit reached."
            )

    # --------------------------------------------------------
    # Simulated Trust Engine (placeholder)
    # --------------------------------------------------------
    trust_score = 95.0  # TODO: replace with real trust engine call

    # --------------------------------------------------------
    # Usage Increment
    # --------------------------------------------------------
    tenant.current_month_usage += 1
    tenant.lifetime_usage += 1
    tenant.last_request_at = datetime.utcnow()

    db.commit()

    # --------------------------------------------------------
    # Latency Calculation
    # --------------------------------------------------------
    latency_ms = int((time.time() - start_time) * 1000)

    return EvaluationResponse(
        request_id=str(uuid4()),
        tenant_id=tenant.tenant_id,
        message="Evaluation successful",
        trust_score=trust_score,
        latency_ms=latency_ms,
        timestamp=datetime.utcnow()
    )