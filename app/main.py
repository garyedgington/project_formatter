from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query, Request

from app.config import get_settings
from app.formatter import convert, validate_output
from app.models import FormatRequest, FormatResponse, HealthResponse, VALID_PAIRS
from app.payment import enforce_payment
from app.telemetry import request_logging_middleware

settings = get_settings()
APP_VERSION = settings.app_version

TRIAL_MAX_BYTES = settings.trial_max_bytes

app = FastAPI(
    title="Project Formatter Agent",
    version=APP_VERSION,
    description=(
        "Convert CSV, XML, or Markdown to JSON or HTML. "
        "POST /v1/format requires x402 USDC micropayment ($0.005). "
        "POST /v1/format/trial is free, no ?validate support, 32KB limit."
    ),
)

if settings.log_requests:
    app.middleware("http")(request_logging_middleware)


@app.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="formatter-agent", version=APP_VERSION)


@app.post("/v1/format", response_model=FormatResponse, dependencies=[Depends(enforce_payment)])
def format_data(
    request: FormatRequest,
    validate: bool = Query(default=False, description="Run a self-validation pass on the output"),
) -> FormatResponse:
    pair = (request.from_format.lower(), request.to_format.lower())

    if pair not in VALID_PAIRS:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNSUPPORTED_CONVERSION",
                "message": f"Conversion from '{request.from_format}' to '{request.to_format}' is not supported.",
                "supported_pairs": [{"from": f, "to": t} for f, t in sorted(VALID_PAIRS)],
            },
        )

    if len(request.input.encode("utf-8")) > settings.max_input_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "INPUT_TOO_LARGE",
                "message": f"Input must not exceed {settings.max_input_bytes // 1024}KB.",
            },
        )

    try:
        result = convert(request.input, pair)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "CONVERSION_FAILED", "message": str(exc)},
        ) from exc

    if validate:
        try:
            valid, errors = validate_output(result, pair[1])
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "VALIDATION_FAILED", "message": str(exc)},
            ) from exc
        return FormatResponse(result=result, valid=valid, errors=errors)

    return FormatResponse(result=result)


@app.post(
    "/v1/format/trial",
    response_model=FormatResponse,
    summary="Trial — no payment required",
    description=(
        "Free trial endpoint. No x402 payment required. "
        "?validate is not supported on trial. Request body must not exceed 32KB. "
        "Use POST /v1/format for full access."
    ),
)
async def format_trial(raw_request: Request, request: FormatRequest) -> FormatResponse:
    body = await raw_request.body()
    if len(body) > TRIAL_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "TRIAL_PAYLOAD_TOO_LARGE",
                "message": f"Trial endpoint request body must not exceed {TRIAL_MAX_BYTES // 1024}KB. "
                           "Use the paid endpoint POST /v1/format for larger inputs.",
            },
        )

    pair = (request.from_format.lower(), request.to_format.lower())
    if pair not in VALID_PAIRS:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNSUPPORTED_CONVERSION",
                "message": f"Conversion from '{request.from_format}' to '{request.to_format}' is not supported.",
                "supported_pairs": [{"from": f, "to": t} for f, t in sorted(VALID_PAIRS)],
            },
        )

    try:
        result = convert(request.input, pair)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "CONVERSION_FAILED", "message": str(exc)},
        ) from exc

    return FormatResponse(result=result)
