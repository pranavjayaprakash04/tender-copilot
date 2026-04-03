"""WhatsApp integration helpers and HMAC webhook verification."""
from __future__ import annotations

import hashlib
import hmac
import os
import structlog

logger = structlog.get_logger()


def verify_whatsapp_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """
    Verify the HMAC-SHA256 signature of a WhatsApp webhook payload.

    Meta sends: X-Hub-Signature-256: sha256=<hex_digest>
    We compute HMAC-SHA256 of the raw payload using WHATSAPP_APP_SECRET.
    """
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "")
    if not app_secret:
        logger.warning("whatsapp_app_secret_missing", detail="WHATSAPP_APP_SECRET env var not set")
        return False

    try:
        # Header format: "sha256=<hex>"
        if not signature_header.startswith("sha256="):
            logger.warning("whatsapp_invalid_signature_header", header=signature_header[:30])
            return False

        received_digest = signature_header.removeprefix("sha256=")
        expected_digest = hmac.new(
            app_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_digest, received_digest)
    except Exception as e:
        logger.error("whatsapp_signature_verification_error", error=str(e))
        return False


def verify_webhook_token(hub_verify_token: str) -> bool:
    """
    Verify the webhook verification token sent by Meta during webhook setup.
    Uses WHATSAPP_VERIFY_TOKEN env var (NOT WHATSAPP_APP_SECRET).
    """
    expected = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    if not expected:
        logger.warning(
            "whatsapp_verify_token_missing",
            detail="WHATSAPP_VERIFY_TOKEN env var not set"
        )
        return False
    return hmac.compare_digest(expected, hub_verify_token)
