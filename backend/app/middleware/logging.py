import time
import uuid

import structlog
from fastapi import Request

logger = structlog.get_logger()

async def logging_middleware(request: Request, call_next):
    """Middleware to log all requests and responses."""
    trace_id = str(uuid.uuid4())
    start_time = time.monotonic()

    # Add trace_id to request state for use in other middleware/endpoints
    request.state.trace_id = trace_id

    # Log request
    logger.info(
        "request_started",
        trace_id=trace_id,
        method=request.method,
        path=str(request.url.path),
        query=dict(request.query_params),
        headers=dict(request.headers),
    )

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = round((time.monotonic() - start_time) * 1000)

    # Log response
    logger.info(
        "request_completed",
        trace_id=trace_id,
        method=request.method,
        path=str(request.url.path),
        status_code=response.status_code,
        duration_ms=duration,
    )

    # Add trace_id to response headers
    response.headers["X-Trace-ID"] = trace_id

    return response
