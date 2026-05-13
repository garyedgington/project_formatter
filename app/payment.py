from __future__ import annotations

import base64
import json
import os
from typing import Any

from fastapi import Header, HTTPException, status

from app.config import Settings, get_settings


X_PAYMENT_HEADER = "X-PAYMENT"
PAYMENT_REQUIRED_HEADER = "PAYMENT-REQUIRED"
PAYMENT_RESPONSE_HEADER = "PAYMENT-RESPONSE"
PAYMENT_SIGNATURE_HEADER = "PAYMENT-SIGNATURE"

PAYMENT_REQUIRED_DETAIL = {
    "code": "PAYMENT_REQUIRED",
    "message": "Payment is required to access this endpoint.",
    "payment_protocol": "x402-placeholder",
    "payment_hint": "Send X-Payment-Token: test-payment-token while placeholder mode is enabled.",
}


def _base64_encode(data: str) -> str:
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


def build_x402_payment_required(settings: Settings, resource_url: str) -> dict[str, Any]:
    """Build a v2 PaymentRequired response body.

    Matches the x402 SDK v2 PaymentRequired schema:
    {
        x402Version: 2,
        resource: { url, description },
        accepts: [ PaymentRequirements ]
    }
    """
    if not settings.x402_pay_to:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "X402_PAY_TO_MISSING", "message": "FORMATTER_X402_PAY_TO is required for x402 mode."},
        )

    return {
        "x402Version": 2,
        "resource": {
            "url": resource_url,
            "description": "Convert CSV, XML, or Markdown to JSON or HTML. Optional self-validation pass returns structural errors.",
            "mimeType": "application/json",
            "serviceName": "Data Formatter Agent",
            "tags": ["csv", "xml", "markdown", "json", "html", "format", "convert", "transform", "agent"],
        },
        "accepts": [
            {
                "scheme": settings.x402_scheme,
                "network": settings.x402_network,
                "asset": settings.x402_asset,
                "amount": settings.x402_amount,
                "payTo": settings.x402_pay_to,
                "maxTimeoutSeconds": settings.x402_max_timeout_seconds,
                # EIP-712 domain for USDC on Base mainnet — required for client signing
                "extra": {
                    "name": "USD Coin",
                    "version": "2",
                },
            }
        ],
        "extensions": {
            "bazaar": {
                "discoverable": True,
                "inputSchema": {
                    "body": {
                        "from": {
                            "type": "string",
                            "description": "Source format: csv | xml | markdown",
                            "required": True,
                        },
                        "to": {
                            "type": "string",
                            "description": "Target format: json | html",
                            "required": True,
                        },
                        "input": {
                            "type": "string",
                            "description": "The raw input content to convert",
                            "required": True,
                        },
                    },
                    "query": {
                        "validate": {
                            "type": "boolean",
                            "description": "If true, run a structural validation pass and return valid + errors[]",
                            "required": False,
                        },
                    },
                },
                "outputSchema": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string",  "description": "Converted output content"},
                        "valid":  {"type": "boolean", "description": "Structural validity of output (only when ?validate=true)"},
                        "errors": {"type": "array",   "description": "List of structural errors (only when ?validate=true and valid=false)"},
                    },
                },
            }
        },
    }


def _raise_x402_payment_required(settings: Settings) -> None:
    resource_url = os.getenv("FORMATTER_RESOURCE_URL", "https://project-formatter-production.up.railway.app/v1/format")
    payment_required = build_x402_payment_required(settings, resource_url)
    header_value = _base64_encode(json.dumps(payment_required, separators=(",", ":")))
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail=payment_required,
        headers={PAYMENT_REQUIRED_HEADER: header_value},
    )


def verify_x402_payment(payment_payload: str, settings: Settings) -> None:
    """Verify x402 payment through the SDK when explicitly enabled."""
    if not settings.x402_real_verification_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "code": "X402_REAL_VERIFICATION_DISABLED",
                "message": "x402 payment payload was received, but live verification is disabled.",
            },
        )

    try:
        from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync
        from x402.mechanisms.evm.exact import ExactEvmServerScheme
        from x402.http.utils import decode_payment_signature_header
        from x402.server import x402ResourceServerSync
        from x402.schemas import PaymentRequirements
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "X402_SDK_UNAVAILABLE", "message": f"Unable to import x402 SDK: {exc}"},
        ) from exc

    try:
        facilitator = HTTPFacilitatorClientSync(FacilitatorConfig(url=settings.x402_facilitator_url))
        resource_server = x402ResourceServerSync(facilitator)
        resource_server.register(settings.x402_network, ExactEvmServerScheme())
        resource_server.initialize()

        requirements = PaymentRequirements(
            scheme=settings.x402_scheme,
            network=settings.x402_network,
            asset=settings.x402_asset,
            amount=settings.x402_amount,
            pay_to=settings.x402_pay_to,
            max_timeout_seconds=settings.x402_max_timeout_seconds,
            extra={"name": "USD Coin", "version": "2"},
        )

        payload = decode_payment_signature_header(payment_payload)
        verify_result = resource_server.verify_payment(payload, requirements)
        if not getattr(verify_result, "is_valid", False):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "X402_PAYMENT_INVALID",
                    "message": "x402 payment verification failed.",
                    "reason": getattr(verify_result, "invalid_reason", None),
                    "detail": getattr(verify_result, "invalid_message", None),
                },
            )

        resource_server.settle_payment(payload, requirements)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "X402_PAYMENT_FAILED", "message": str(exc)},
        ) from exc


def enforce_payment(
    x_payment_token: str | None = Header(default=None, alias="X-Payment-Token"),
    x_payment: str | None = Header(default=None, alias="X-PAYMENT"),
    payment_signature: str | None = Header(default=None, alias="PAYMENT-SIGNATURE"),
) -> None:
    """Payment gate for disabled, placeholder, and x402 modes.

    x402 v2 clients send PAYMENT-SIGNATURE (not X-PAYMENT).
    x402 v1 clients send X-PAYMENT.
    Both are accepted.
    """
    settings = get_settings()

    if settings.payment_mode == "disabled":
        return

    if settings.payment_mode == "placeholder":
        if x_payment_token != settings.placeholder_payment_token:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=PAYMENT_REQUIRED_DETAIL)
        return

    if settings.payment_mode == "x402":
        payment_payload = payment_signature or x_payment
        if not payment_payload:
            _raise_x402_payment_required(settings)
        verify_x402_payment(payment_payload, settings)
        return

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"code": "PAYMENT_GATE_MISCONFIGURED", "message": f"Unsupported payment mode: {settings.payment_mode}"},
    )


