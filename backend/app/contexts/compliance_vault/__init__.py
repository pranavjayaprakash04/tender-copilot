"""Compliance Vault Context.

Handles document storage, classification, expiry tracking, and tender-document mapping.
"""

from .models import DocumentType, VaultDocument, VaultDocumentMapping
from .repository import VaultDocumentMappingRepository, VaultDocumentRepository
from .router import router
from .schemas import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
    DocumentListResponse,
    DocumentSearchFilters,
    DocumentStatsResponse,
    TenderDocumentMappingCreate,
    TenderDocumentMappingResponse,
    VaultDocumentCreate,
    VaultDocumentResponse,
    VaultDocumentUpdate,
)
from .service import ComplianceVaultService

__all__ = [
    "VaultDocument",
    "VaultDocumentMapping",
    "DocumentType",
    "VaultDocumentResponse",
    "VaultDocumentCreate",
    "VaultDocumentUpdate",
    "DocumentListResponse",
    "DocumentStatsResponse",
    "DocumentClassificationRequest",
    "DocumentClassificationResponse",
    "TenderDocumentMappingCreate",
    "TenderDocumentMappingResponse",
    "DocumentSearchFilters",
    "ComplianceVaultService",
    "VaultDocumentRepository",
    "VaultDocumentMappingRepository",
    "router",
]
