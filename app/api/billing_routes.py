from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, AuthContext
from app.models.tenant import Tenant
from app.models.usage_meter import UsageMeter
from app.models.pricing_plan import PricingPlan

router = APIRouter()


# ===================================================
# 📊 GET CURRENT MONTH BILLING SUMMARY
# ===================================================
@router.get("/billing")
def get_billing(
    auth: AuthContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    Returns detailed billing summary for the authenticated tenant.
    Includes:
    - Base plan cost
    - Overage cost
    - Semantic usage cost
    - Latency metrics
    """

    tenant_id = auth.tenant_id
    current_month = datetime.utcnow().strftime("%Y-%m")

    # ---------------------------------------------------
    # 1️⃣ Validate Tenant
    # ---------------------------------------------------
    tenant = db.query(Tenant).filter(
        Tenant.tenant_id == tenant_id,
        Tenant.is_active == True,
        Tenant.is_suspended == False
    ).first()

    if not tenant:
        raise HTTPException(
            status_code=403,
            detail="Tenant inactive or suspended"
        )

    # ---------------------------------------------------
    # 2️⃣ Fetch Usage
    # ---------------------------------------------------
    usage = db.query(UsageMeter).filter(
        UsageMeter.tenant_id == tenant_id,
        UsageMeter.month == current_month
    ).first()

    if not usage:
        return {
            "tenant_id": tenant_id,
            "month": current_month,
            "plan": tenant.plan,
            "total_requests": 0,
            "semantic_calls": 0,
            "estimated_cost": 0.0,
            "generated_at": datetime.utcnow()
        }

    # ---------------------------------------------------
    # 3️⃣ Fetch Pricing Plan
    # ---------------------------------------------------
    plan = db.query(PricingPlan).filter(
        PricingPlan.name == tenant.plan
    ).first()

    if not plan:
        raise HTTPException(
            status_code=500,
            detail="Pricing plan configuration missing"
        )

    # ---------------------------------------------------
    # 4️⃣ Cost Calculation (Financially Safe)
    # ---------------------------------------------------

    base_cost = Decimal(str(plan.monthly_price))

    extra_requests = max(
        0,
        usage.total_requests - plan.request_limit
    )

    overage_cost = (
        Decimal(extra_requests)
        * Decimal(str(plan.overage_per_request))
    )

    semantic_cost = (
        Decimal(usage.semantic_calls)
        * Decimal(str(plan.semantic_call_cost))
    )

    total_estimated_cost = (
        base_cost + overage_cost + semantic_cost
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # ---------------------------------------------------
    # 5️⃣ Persist Estimated Cost (Only if Changed)
    # ---------------------------------------------------
    if float(usage.estimated_cost) != float(total_estimated_cost):
        usage.estimated_cost = float(total_estimated_cost)
        db.commit()

    # ---------------------------------------------------
    # 6️⃣ Latency Metrics
    # ---------------------------------------------------
    avg_latency = (
        usage.total_latency_ms / usage.total_requests
        if usage.total_requests > 0 else 0
    )

    # ---------------------------------------------------
    # 7️⃣ Response
    # ---------------------------------------------------
    return {
        "tenant_id": tenant_id,
        "month": current_month,
        "plan": plan.name,
        "monthly_base_price": float(base_cost),
        "request_limit": plan.request_limit,

        "total_requests": usage.total_requests,
        "extra_requests": extra_requests,
        "overage_cost": float(overage_cost),

        "semantic_calls": usage.semantic_calls,
        "semantic_cost": float(semantic_cost),

        "estimated_cost": float(total_estimated_cost),

        "avg_latency_ms": int(avg_latency),

        "generated_at": datetime.utcnow()
    }