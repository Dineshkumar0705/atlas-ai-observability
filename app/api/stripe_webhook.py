import os
import stripe
import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.pricing_plan import PricingPlan

# ===================================================
# Setup
# ===================================================

load_dotenv()

router = APIRouter()
logger = logging.getLogger("ATLAS-STRIPE")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if not WEBHOOK_SECRET:
    logger.warning("⚠ STRIPE_WEBHOOK_SECRET not configured")


# ===================================================
# 🔔 STRIPE WEBHOOK ENDPOINT
# ===================================================
@router.post("/stripe/webhook", response_model=None)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handles Stripe subscription lifecycle events.

    Events handled:
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_failed
    - invoice.payment_succeeded
    """

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # ===================================================
    # Verify Signature
    # ===================================================
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid Stripe signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.exception(f"Webhook parsing error: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook error")

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Stripe event received: {event_type}")

    # ===================================================
    # 🟢 CHECKOUT COMPLETED
    # ===================================================
    if event_type == "checkout.session.completed":

        customer_id = data.get("customer")
        subscription_id = data.get("subscription")

        tenant = db.query(Tenant).filter(
            Tenant.stripe_customer_id == customer_id
        ).first()

        if tenant and subscription_id:
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                price_id = subscription["items"]["data"][0]["price"]["id"]

                plan = db.query(PricingPlan).filter(
                    PricingPlan.stripe_price_id == price_id
                ).first()

                if plan:
                    tenant.plan = plan.name
                    tenant.monthly_request_limit = plan.request_limit
                    tenant.stripe_subscription_id = subscription_id
                    tenant.is_suspended = False

                    db.commit()
                    logger.info(f"Tenant {tenant.tenant_id} upgraded to {plan.name}")

            except Exception as e:
                logger.exception(f"Subscription activation error: {str(e)}")

    # ===================================================
    # 🔄 SUBSCRIPTION UPDATED
    # ===================================================
    elif event_type == "customer.subscription.updated":

        customer_id = data.get("customer")
        price_id = data["items"]["data"][0]["price"]["id"]

        tenant = db.query(Tenant).filter(
            Tenant.stripe_customer_id == customer_id
        ).first()

        if tenant:
            plan = db.query(PricingPlan).filter(
                PricingPlan.stripe_price_id == price_id
            ).first()

            if plan:
                tenant.plan = plan.name
                tenant.monthly_request_limit = plan.request_limit
                db.commit()
                logger.info(f"Tenant {tenant.tenant_id} plan updated")

    # ===================================================
    # 🔴 SUBSCRIPTION CANCELLED
    # ===================================================
    elif event_type == "customer.subscription.deleted":

        customer_id = data.get("customer")

        tenant = db.query(Tenant).filter(
            Tenant.stripe_customer_id == customer_id
        ).first()

        if tenant:
            tenant.plan = "free"
            tenant.monthly_request_limit = 1000
            tenant.stripe_subscription_id = None
            tenant.is_suspended = False
            db.commit()

            logger.info(f"Tenant {tenant.tenant_id} downgraded to free")

    # ===================================================
    # 🔴 PAYMENT FAILED → SUSPEND
    # ===================================================
    elif event_type == "invoice.payment_failed":

        customer_id = data.get("customer")

        tenant = db.query(Tenant).filter(
            Tenant.stripe_customer_id == customer_id
        ).first()

        if tenant:
            tenant.is_suspended = True
            db.commit()

            logger.warning(f"Tenant {tenant.tenant_id} suspended due to failed payment")

    # ===================================================
    # 🟢 PAYMENT SUCCEEDED → REACTIVATE
    # ===================================================
    elif event_type == "invoice.payment_succeeded":

        customer_id = data.get("customer")

        tenant = db.query(Tenant).filter(
            Tenant.stripe_customer_id == customer_id
        ).first()

        if tenant:
            tenant.is_suspended = False
            db.commit()

            logger.info(f"Tenant {tenant.tenant_id} reactivated")

    return JSONResponse({"status": "success"})