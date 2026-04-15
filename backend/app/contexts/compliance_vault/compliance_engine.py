from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.compliance_vault.models import DocumentType, VaultDocument
from app.contexts.compliance_vault.repository import VaultDocumentRepository
from app.contexts.tender_discovery.models import Tender
from app.shared.exceptions import ComplianceException

logger = structlog.get_logger()


class ComplianceRule(StrEnum):
    """Hard-coded compliance rules that CANNOT be overridden by AI."""
    GST_REGISTRATION = "gst"
    PAN_CARD = "pan"
    UDYAM_MSME = "udyam"
    BANK_GUARANTEE = "bank_guarantee"
    AUDIT_STATEMENT = "audit_statement"
    EXPERIENCE_CERTIFICATE = "experience_certificate"
    TAX_CLEARANCE = "tax_clearance"
    ISO_CERTIFICATION = "iso"
    TRADE_LICENSE = "trade_license"


class ComplianceSeverity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ComplianceCheckResult:
    is_compliant: bool
    missing_documents: list[ComplianceRule]
    expired_documents: list[tuple[ComplianceRule, datetime]]
    severity: ComplianceSeverity
    audit_trail: dict[str, Any] = field(default_factory=dict)


class HardComplianceEngine:
    """
    ZERO-TOLERANCE compliance engine.
    Runs BEFORE AI generation. Cannot be bypassed.
    One missing document = bid generation BLOCKED.
    """
    
    # Tender value thresholds (in INR)
    HIGH_VALUE_THRESHOLD = 10_00_000  # 10 Lakhs
    VERY_HIGH_VALUE = 50_00_000  # 50 Lakhs
    
    # Document requirements by tender characteristics
    RULES_CONFIG = {
        "universal": [ComplianceRule.PAN_CARD, ComplianceRule.GST_REGISTRATION],
        "msme_preference": [ComplianceRule.UDYAM_MSME],
        "high_value": [ComplianceRule.AUDIT_STATEMENT, ComplianceRule.TAX_CLEARANCE],
        "technical": [ComplianceRule.EXPERIENCE_CERTIFICATE, ComplianceRule.ISO_CERTIFICATION],
    }
    
    def __init__(self, session: AsyncSession):
        self._doc_repo = VaultDocumentRepository(session)
        self._audit_log = []
    
    async def validate_before_generation(
        self,
        company_id: UUID,
        tender: Tender,
        bid_type: str,
        trace_id: str | None = None
    ) -> ComplianceCheckResult:
        """
        MANDATORY gate before AI generation.
        If this returns is_compliant=False, AI generation is BLOCKED.
        """
        logger.info(
            "compliance_validation_started",
            trace_id=trace_id,
            company_id=str(company_id),
            tender_id=str(tender.id) if hasattr(tender, 'id') else 'unknown',
            tender_value=getattr(tender, 'tender_value', None)
        )
        
        # Determine required documents
        required_docs = self._determine_required_docs(tender, bid_type)
        
        # Fetch current valid documents
        company_docs = await self._get_current_documents(company_id)
        doc_map = {doc.doc_type: doc for doc in company_docs}
        
        # Hard validation
        missing = []
        expired = []
        
        for rule in required_docs:
            doc = doc_map.get(self._rule_to_doc_type(rule))
            
            if not doc:
                missing.append(rule)
                self._audit_log.append({
                    "rule": rule.value,
                    "status": "missing",
                    "timestamp": datetime.now(UTC).isoformat()
                })
            elif doc.is_expired:
                expired.append((rule, doc.expires_at))
                self._audit_log.append({
                    "rule": rule.value,
                    "status": "expired",
                    "document_id": str(doc.id),
                    "expired_at": doc.expires_at.isoformat() if doc.expires_at else None,
                    "timestamp": datetime.now(UTC).isoformat()
                })
            else:
                self._audit_log.append({
                    "rule": rule.value,
                    "status": "valid",
                    "document_id": str(doc.id),
                    "expires_at": doc.expires_at.isoformat() if doc.expires_at else None,
                    "timestamp": datetime.now(UTC).isoformat()
                })
        
        # Determine severity
        severity = self._calculate_severity(missing, expired, tender)
        is_compliant = len(missing) == 0 and len(expired) == 0
        
        result = ComplianceCheckResult(
            is_compliant=is_compliant,
            missing_documents=missing,
            expired_documents=expired,
            severity=severity,
            audit_trail={
                "validation_timestamp": datetime.now(UTC).isoformat(),
                "tender_id": str(tender.id) if hasattr(tender, 'id') else None,
                "company_id": str(company_id),
                "required_rules": [r.value for r in required_docs],
                "checks": self._audit_log,
                "validator_version": "2.0.0-hard"
            }
        )
        
        logger.info(
            "compliance_validation_completed",
            trace_id=trace_id,
            is_compliant=is_compliant,
            missing_count=len(missing),
            expired_count=len(expired),
            severity=severity.value
        )
        
        return result
    
    def _determine_required_docs(self, tender: Tender, bid_type: str) -> list[ComplianceRule]:
        """Determine mandatory documents for this tender."""
        required = list(self.RULES_CONFIG["universal"])
        
        tender_value = getattr(tender, 'tender_value', None)
        if tender_value and tender_value > self.HIGH_VALUE_THRESHOLD:
            required.extend(self.RULES_CONFIG["high_value"])
        
        if tender_value and tender_value > self.VERY_HIGH_VALUE:
            required.append(ComplianceRule.BANK_GUARANTEE)
        
        if bid_type in ["technical", "combined"]:
            required.extend(self.RULES_CONFIG["technical"])
        
        # Check for MSME preference
        if hasattr(tender, 'msme_preference') and tender.msme_preference:
            required.extend(self.RULES_CONFIG["msme_preference"])
        
        return list(set(required))
    
    async def _get_current_documents(self, company_id: UUID) -> list[VaultDocument]:
        """Get non-expired documents for company."""
        # Use existing repo method or create one
        return await self._doc_repo.get_by_company(company_id)
    
    def _rule_to_doc_type(self, rule: ComplianceRule) -> DocumentType:
        """Map compliance rule to document type."""
        mapping = {
            ComplianceRule.GST_REGISTRATION: DocumentType.GST,
            ComplianceRule.PAN_CARD: DocumentType.PAN,
            ComplianceRule.UDYAM_MSME: DocumentType.UDYAM,
            ComplianceRule.BANK_GUARANTEE: DocumentType.BANK_GUARANTEE,
            ComplianceRule.AUDIT_STATEMENT: DocumentType.FINANCIAL_STATEMENT,
            ComplianceRule.EXPERIENCE_CERTIFICATE: DocumentType.EXPERIENCE_CERTIFICATE,
            ComplianceRule.TAX_CLEARANCE: DocumentType.TAX_CLEARANCE,
            ComplianceRule.ISO_CERTIFICATION: DocumentType.ISO,
            ComplianceRule.TRADE_LICENSE: DocumentType.TRADE_LICENSE,
        }
        return mapping.get(rule, DocumentType.OTHER)
    
    def _calculate_severity(
        self,
        missing: list[ComplianceRule],
        expired: list[tuple[ComplianceRule, datetime]],
        tender: Tender
    ) -> ComplianceSeverity:
        """Calculate blocking severity."""
        critical_docs = {ComplianceRule.PAN_CARD, ComplianceRule.GST_REGISTRATION}
        
        if any(m in critical_docs for m in missing):
            return ComplianceSeverity.BLOCKING
        
        tender_value = getattr(tender, 'tender_value', 0) or 0
        if (tender_value > self.HIGH_VALUE_THRESHOLD and 
            ComplianceRule.AUDIT_STATEMENT in missing):
            return ComplianceSeverity.BLOCKING
        
        if any(rule in critical_docs for rule, _ in expired):
            return ComplianceSeverity.CRITICAL
        
        return ComplianceSeverity.WARNING if (missing or expired) else ComplianceSeverity.BLOCKING


# Add to repository
async def get_current_documents(self, company_id: UUID) -> list[VaultDocument]:
    """Get current valid documents only."""
    from sqlalchemy import select
    from datetime import datetime
    
    stmt = (
        select(VaultDocument)
        .where(VaultDocument.company_id == company_id)
        .where(VaultDocument.is_current == True)
    )
    result = await self._session.execute(stmt)
    return result.scalars().all()
