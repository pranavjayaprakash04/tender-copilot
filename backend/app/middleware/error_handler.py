import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from app.shared.exceptions import AppException

logger = structlog.get_logger()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "*",
}


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
        headers=CORS_HEADERS,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        path=str(request.url),
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
                "trace_id": None,
                "detail": None,
            }
        },
        headers=CORS_HEADERS,
    )
