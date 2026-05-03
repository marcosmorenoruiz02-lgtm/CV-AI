"""Stripe Checkout integration for the CVBoost Pro subscription (5 EUR / month).

This router exposes:
    POST /api/payments/checkout/session        — start a new Checkout session (auth'd)
    GET  /api/payments/checkout/status/{id}    — poll session status & flip user → PRO
    POST /api/webhook/stripe                   — Stripe webhook sink (no auth)

We intentionally use a single fixed backend-side package (CVBoost Pro, 5 EUR, 30 days
of unlimited access). Prices NEVER come from the client — this prevents frontend
amount tampering (see security checklist in the Stripe playbook).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from emergentintegrations.payments.stripe.checkout import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CheckoutStatusResponse,
    StripeCheckout,
)
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from deps import User, db, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["payments"])

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")

# Fixed server-side package. The frontend never supplies amount/currency.
PRO_PACKAGE = {
    "id": "cvboost_pro_monthly",
    "name": "CVBoost Pro (1 mes)",
    "amount": 5.00,
    "currency": "eur",
    "period_days": 30,
}


class CreateCheckoutRequest(BaseModel):
    origin_url: str
    package_id: str = "cvboost_pro_monthly"


def _checkout_client(request: Request) -> StripeCheckout:
    if not STRIPE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="STRIPE_API_KEY missing in backend .env",
        )
    webhook_url = f"{str(request.base_url).rstrip('/')}/api/webhook/stripe"
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)


async def _grant_pro_access(user_id: str, session_id: str, months: int = 1) -> None:
    """Atomically flip a user to PRO and extend pro_expires_at by N months (30-day blocks).

    Idempotency is controlled by the caller via `payment_transactions.pro_granted` flag,
    so that the webhook and the poll-based status endpoint can never double-extend Pro
    access for the same Stripe session.
    """
    # Atomic compare-and-set: only the first caller wins and flips pro_granted=True.
    res = await db.payment_transactions.update_one(
        {"session_id": session_id, "pro_granted": {"$ne": True}},
        {"$set": {"pro_granted": True, "pro_granted_at": datetime.now(timezone.utc).isoformat()}},
    )
    if res.modified_count == 0:
        return  # Another caller already granted Pro for this session.

    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        logger.error("Stripe success for unknown user_id=%s session=%s", user_id, session_id)
        return

    now = datetime.now(timezone.utc)
    current = user.get("pro_expires_at")
    if isinstance(current, str):
        try:
            current = datetime.fromisoformat(current)
        except ValueError:
            current = None
    if current and current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    base = current if (current and current > now) else now
    new_expiry = base + timedelta(days=30 * months)

    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "tier": "PRO",
                "pro_expires_at": new_expiry.isoformat(),
            }
        },
    )


@router.post("/payments/checkout/session")
async def create_checkout_session(
    payload: CreateCheckoutRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    if payload.package_id != PRO_PACKAGE["id"]:
        raise HTTPException(status_code=400, detail="Paquete desconocido")

    origin = payload.origin_url.rstrip("/")
    success_url = f"{origin}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/payment/cancel"

    client = _checkout_client(request)
    checkout_req = CheckoutSessionRequest(
        amount=PRO_PACKAGE["amount"],
        currency=PRO_PACKAGE["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user.user_id,
            "user_email": user.email,
            "package_id": PRO_PACKAGE["id"],
            "source": "cvboost_upgrade",
        },
    )

    try:
        session: CheckoutSessionResponse = await client.create_checkout_session(checkout_req)
    except Exception as e:
        logger.exception("Stripe create_checkout_session failed")
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")

    await db.payment_transactions.insert_one(
        {
            "session_id": session.session_id,
            "user_id": user.user_id,
            "user_email": user.email,
            "package_id": PRO_PACKAGE["id"],
            "amount": PRO_PACKAGE["amount"],
            "currency": PRO_PACKAGE["currency"],
            "status": "initiated",
            "payment_status": "pending",
            "metadata": {
                "user_id": user.user_id,
                "package_id": PRO_PACKAGE["id"],
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    return {"url": session.url, "session_id": session.session_id}


@router.get("/payments/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, request: Request):
    """Return the current payment status for a session.

    The Emergent Stripe test proxy only supports create + webhook, not retrieve.
    So we primarily trust our local `payment_transactions` row (updated by the
    webhook). We only try Stripe as a best-effort fallback when the local row
    is still pending, so the flow still works with real Stripe keys in prod.
    """
    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # If the webhook already marked this paid, we're done — skip Stripe roundtrip.
    if tx.get("payment_status") == "paid":
        return {
            "session_id": session_id,
            "status": tx.get("status") or "complete",
            "payment_status": "paid",
            "amount_total": int((tx.get("amount") or 0) * 100),
            "currency": tx.get("currency") or "eur",
        }

    # Otherwise, try Stripe (works with real keys, may fail on the emergent test proxy).
    client = _checkout_client(request)
    try:
        status: CheckoutStatusResponse = await client.get_checkout_status(session_id)
    except Exception as e:
        logger.info("Stripe get_checkout_status unavailable (will rely on webhook): %s", e)
        return {
            "session_id": session_id,
            "status": tx.get("status") or "initiated",
            "payment_status": tx.get("payment_status") or "pending",
            "amount_total": int((tx.get("amount") or 0) * 100),
            "currency": tx.get("currency") or "eur",
        }

    # Update transaction row once per terminal state change (idempotent).
    needs_update = (
        tx.get("status") != status.status
        or tx.get("payment_status") != status.payment_status
    )
    if needs_update:
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "status": status.status,
                    "payment_status": status.payment_status,
                    "amount_total": status.amount_total,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    if status.payment_status == "paid" and tx.get("payment_status") != "paid":
        user_id = tx.get("user_id") or (status.metadata or {}).get("user_id")
        if user_id:
            await _grant_pro_access(user_id, session_id, months=1)

    return {
        "session_id": session_id,
        "status": status.status,
        "payment_status": status.payment_status,
        "amount_total": status.amount_total,
        "currency": status.currency,
    }


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Best-effort webhook sink. Frontend polling is the primary source of truth; this is
    just an extra safety net in case the user closes the browser before the redirect.
    """
    client = _checkout_client(request)
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")

    try:
        event = await client.handle_webhook(body, sig)
    except Exception as e:
        logger.warning("Webhook signature/validation failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid webhook")

    # Fields per playbook: event_type, event_id, session_id, payment_status, metadata
    if event.payment_status == "paid" and event.session_id:
        tx = await db.payment_transactions.find_one(
            {"session_id": event.session_id}, {"_id": 0}
        )
        if tx and tx.get("payment_status") != "paid":
            await db.payment_transactions.update_one(
                {"session_id": event.session_id},
                {
                    "$set": {
                        "payment_status": "paid",
                        "status": "complete",
                        "webhook_received_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
            user_id = tx.get("user_id") or (event.metadata or {}).get("user_id")
            if user_id:
                await _grant_pro_access(user_id, event.session_id, months=1)

    return {"received": True}


@router.get("/payments/pro-package")
async def get_pro_package():
    """Public read-only metadata so the frontend can display price/period without hardcoding."""
    return PRO_PACKAGE
