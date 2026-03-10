import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppException(Exception):
    message: str
    code: str
    status_code: int = 500
    detail: Any = None
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class ValidationException(AppException):
    def __init__(self, message: str, detail: Any = None) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR",
                         status_code=422, detail=detail)


class NotFoundException(AppException):
    def __init__(self, resource: str) -> None:
        super().__init__(message=f"{resource} not found",
                         code="NOT_FOUND", status_code=404)


class AuthorizationException(AppException):
    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message=message, code="FORBIDDEN", status_code=403)


class LLMException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="LLM_ERROR", status_code=502)


class ExternalServiceException(AppException):
    def __init__(self, service: str, message: str) -> None:
        super().__init__(message=f"{service}: {message}",
                         code="EXTERNAL_SERVICE_ERROR", status_code=502)


class DatabaseException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="DATABASE_ERROR", status_code=500)


class AuthenticationException(AppException):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message=message, code="AUTHENTICATION_ERROR", status_code=401)


class RateLimitException(AppException):
    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message=message, code="RATE_LIMIT_EXCEEDED", status_code=429)


class FileUploadException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="FILE_UPLOAD_ERROR", status_code=400)


class ComplianceException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="COMPLIANCE_ERROR", status_code=400)


class TenderException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="TENDER_ERROR", status_code=400)


class BidException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="BID_ERROR", status_code=400)


class WhatsAppException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="WHATSAPP_ERROR", status_code=502)


class PaymentException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="PAYMENT_ERROR", status_code=402)
