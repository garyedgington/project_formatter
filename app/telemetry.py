from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Request, Response

logger = logging.getLogger("formatter")
logging.basicConfig(level=logging.INFO, format="%(message)s")


async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    start = time.perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        status_code = response.status_code if response is not None else 500
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            status_code,
            duration_ms,
        )
        if response is not None:
            response.headers["X-Request-ID"] = request_id
