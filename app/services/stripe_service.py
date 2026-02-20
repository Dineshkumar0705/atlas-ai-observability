import os
import stripe
from dotenv import load_dotenv
from typing import Optional, Dict

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class StripeService:
    """
    Centralized Stripe integration layer for ATLAS SaaS.

    Responsibilities:
    - Customer creation
    - Subscription checkout
    - Billing portal
    - Subscription management
    - Safe Stripe API interaction
    """

    SUCCESS_URL = os.getenv(
        "STRIPE_SUCCESS_URL",
        "http://localhost:3000/success"
    )

    CANCEL_URL = os.getenv(
        "STRIPE_CANCEL_URL",
        "http://localhost:3000/cancel"
    )

    PORTAL_RETURN_URL = os.getenv(
        "STRIPE_PORTAL_RETURN_URL",
        "http://localhost:3000/dashboard"
    )

    # ===================================================
    # 👤 Create Stripe Customer
    # ===================================================
    @staticmethod
    def create_customer(email: str, tenant_id: str) -> stripe.Customer:
        try:
            return stripe.Customer.create(
                email=email,
                metadata={
                    "tenant_id": tenant_id,
                    "source": "atlas"
                }
            )
        except Exception as e:
            raise Exception(f"Stripe customer creation failed: {str(e)}")

    # ===================================================
    # 💳 Create Subscription Checkout Session
    # ===================================================
    @staticmethod
    def create_checkout_session(
        customer_id: str,
        price_id: str,
        tenant_id: str,
        plan: str,
        metadata: Optional[Dict] = None
    ) -> stripe.checkout.Session:

        try:
            return stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=StripeService.SUCCESS_URL,
                cancel_url=StripeService.CANCEL_URL,
                metadata={
                    "tenant_id": tenant_id,
                    "plan": plan,
                    **(metadata or {})
                }
            )
        except Exception as e:
            raise Exception(f"Stripe checkout creation failed: {str(e)}")

    # ===================================================
    # 🧾 Create Billing Portal Session
    # ===================================================
    @staticmethod
    def create_billing_portal(customer_id: str) -> stripe.billing_portal.Session:
        try:
            return stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=StripeService.PORTAL_RETURN_URL
            )
        except Exception as e:
            raise Exception(f"Stripe portal creation failed: {str(e)}")

    # ===================================================
    # 🔄 Cancel Subscription
    # ===================================================
    @staticmethod
    def cancel_subscription(subscription_id: str):
        try:
            return stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
        except Exception as e:
            raise Exception(f"Stripe cancellation failed: {str(e)}")

    # ===================================================
    # 🔁 Retrieve Subscription
    # ===================================================
    @staticmethod
    def retrieve_subscription(subscription_id: str):
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except Exception as e:
            raise Exception(f"Stripe retrieval failed: {str(e)}")

    # ===================================================
    # 📦 Upgrade/Downgrade Plan
    # ===================================================
    @staticmethod
    def update_subscription_price(
        subscription_id: str,
        new_price_id: str
    ):
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)

            return stripe.Subscription.modify(
                subscription_id,
                items=[{
                    "id": subscription["items"]["data"][0]["id"],
                    "price": new_price_id,
                }],
                proration_behavior="create_prorations"
            )

        except Exception as e:
            raise Exception(f"Stripe update failed: {str(e)}")