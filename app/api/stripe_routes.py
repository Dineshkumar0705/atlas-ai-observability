from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
import stripe

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, AuthContext
from app.models.tenant import Tenant
from app.models.pricing_plan import PricingPlan
from app.services.stripe_service import StripeService

load_dotenv()

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

FRONTEND_SUCCESS_URL = os.getenv(
    "STRIPE_SUCCESS_URL",
    "http://localhost:3000/success"
)

FRONTEND_CANCEL_URL = os.getenv(
    "STRIPE_CANCEL_URL",
    "http://localhost:3000/cancel"
)


# ===================================================
# 💳 CREATE CHECKOUT SESSION (SUBSCRIPTION)
# ===================================================
@router.post("/stripe/checkout")
def create_checkout(
    plan: str,
    auth: AuthContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):

    tenant_id = auth.tenant_id

    # ---------------------------------------------------
    # 1️⃣ Validate Tenant
    # ---------------------------------------------------
    tenant = db.query(Tenant).filter(
        Tenant.tenant_id == tenant_id,
        Tenant.is_active == True,
        Tenant.is_suspended == False
    ).first()

    if not tenant:
        raise HTTPException(status_code=403, detail="Tenant inactive")

    # ---------------------------------------------------
    # 2️⃣ Validate Plan Exists in DB
    # ---------------------------------------------------
    pricing_plan = db.query(PricingPlan).filter(
        PricingPlan.name == plan,
        PricingPlan.is_active == True
    ).first()

    if not pricing_plan:
        raise HTTPException(status_code=400, detail="Invalid plan selected")

    # Prevent subscribing to same plan
    if tenant.plan == plan and tenant.subscription_status == "active":
        raise HTTPException(
            status_code=400,
            detail="Already subscribed to this plan"
        )

    # ---------------------------------------------------
    # 3️⃣ Resolve Stripe Price ID
    # ---------------------------------------------------
    price_id = os.getenv(f"STRIPE_PRICE_{plan.upper()}")

    if not price_id:
        raise HTTPException(
            status_code=500,
            detail="Stripe price not configured for this plan"
        )

    # ---------------------------------------------------
    # 4️⃣ Create Stripe Customer (If Not Exists)
    # ---------------------------------------------------
    if not tenant.stripe_customer_id:

        if not tenant.owner_email:
            raise HTTPException(
                status_code=400,
                detail="Tenant email required for billing"
            )

        customer = StripeService.create_customer(
            email=tenant.owner_email,
            tenant_id=tenant.tenant_id
        )

        tenant.stripe_customer_id = customer.id
        db.commit()

    # ---------------------------------------------------
    # 5️⃣ Create Checkout Session
    # ---------------------------------------------------
    try:
        session = stripe.checkout.Session.create(
            customer=tenant.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=FRONTEND_SUCCESS_URL,
            cancel_url=FRONTEND_CANCEL_URL,
            metadata={
                "tenant_id": tenant.tenant_id,
                "plan": plan
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Stripe checkout failed: {str(e)}"
        )

    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "plan": plan
    }