import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from app.shared.exceptions import AppException

logger = structlog.get_logger()

async def global_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.error(
        "request_error",
        code=exc.code,
        message=exc.message,
        trace_id=exc.trace_id,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "trace_id": exc.trace_id,
                "detail": exc.detail,
            }
        },
    )
