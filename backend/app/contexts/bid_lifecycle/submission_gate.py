from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

import structlog

from app.contexts.compliance_vault.compliance_engine import HardComplianceEngine
from app.shared.exceptions import ValidationException

logger = structlog.get_logger()


class SubmissionCheck(StrEnum):
    COMPLIANCE_DOCS = "compliance_docs"
    EMD_PAYMENT = "emd_payment"
    TECHNICAL_REVIEW = "technical_review"
    FINANCIAL_VALIDATION = "financial_validation"
    LEGAL_TERMS = "legal_terms"
    DIGITAL_SIGNATURE = "digital_signature"


@dataclass
class SubmissionResult:
    can_submit: bool
    passed_checks: list[str]
    failed_checks: list[str]
    blocking_reason: str | None = None
    audit_trail: dict[str, Any] | None = None


class SubmissionGate:
    """
    FINAL 6-POINT CHECKLIST before bid submission.
    ALL checks must pass. Cannot be bypassed.
    """
    
    REQUIRED_CHECKS = [
        SubmissionCheck.COMPLIANCE_DOCS,
        SubmissionCheck.EMD_PAYMENT,
        SubmissionCheck.TECHNICAL_REVIEW,
        SubmissionCheck.FINANCIAL_VALIDATION,
        SubmissionCheck.LEGAL_TERMS,
        SubmissionCheck.DIGITAL_SIGNATURE,
    ]
    
    def __init__(self, session, compliance_engine: HardComplianceEngine):
        self.session = session
        self.compliance = compliance_engine
    
    async def validate_submission(
        self,
        bid_id: UUID,
        company_id: UUID,
        checklist_signatures: dict[str, bool],
        trace_id: str | None = None
    ) -> SubmissionResult:
        """
        Final validation before submission.
        Returns can_submit=True ONLY if all 6 checks pass.
        """
        logger.info("submission_validation_started", bid_id=str(bid_id), trace_id=trace_id)
        
        passed = []
        failed = []
        audit_log = []
        
        # Check 1: Compliance Docs (Re-verify - may have expired since generation)
        from app.contexts.bid_generation.repository import BidGenerationRepository
        from app.contexts.tender_discovery.repository import TenderRepository
        
        bid_repo = BidGenerationRepository(self.session)
        tender_repo = TenderRepository(self.session)
        
        bid = await bid_repo.get_by_id(bid_id, company_id)
        if not bid:
            raise ValidationException("Bid not found")
        
        tender = await tender_repo.get_by_id(bid.tender_id, company_id)
        
        compliance_result = await self.compliance.validate_before_generation(
            company_id=company_id,
            tender_value=getattr(tender, 'tender_value', None),
            bid_type=bid.bid_type if hasattr(bid, 'bid_type') else 'technical',
            is_msme_preference=getattr(tender, 'msme_preference', False),
            trace_id=trace_id
        )
        
        if compliance_result.is_compliant:
            passed.append(SubmissionCheck.COMPLIANCE_DOCS.value)
            audit_log.append({"check": "compliance", "status": "PASSED"})
        else:
            failed.append(SubmissionCheck.COMPLIANCE_DOCS.value)
            audit_log.append({
                "check": "compliance",
                "status": "FAILED",
                "missing": [m.value for m in compliance_result.missing_documents]
            })
        
        # Check 2: EMD Payment
        emd_amount = getattr(tender, 'emd_amount', 0) or 0
        if emd_amount == 0:
            passed.append(SubmissionCheck.EMD_PAYMENT.value)
            audit_log.append({"check": "emd", "status": "NOT_REQUIRED"})
        else:
            # Check if EMD paid (implement based on your payment model)
            emd_paid = checklist_signatures.get(SubmissionCheck.EMD_PAYMENT.value, False)
            if emd_paid:
                passed.append(SubmissionCheck.EMD_PAYMENT.value)
                audit_log.append({"check": "emd", "status": "PAID", "amount": emd_amount})
            else:
                failed.append(SubmissionCheck.EMD_PAYMENT.value)
                audit_log.append({"check": "emd", "status": "UNPAID", "required": emd_amount})
        
        # Check 3-6: Digital Signatures
        for check in [
            SubmissionCheck.TECHNICAL_REVIEW,
            SubmissionCheck.FINANCIAL_VALIDATION,
            SubmissionCheck.LEGAL_TERMS,
            SubmissionCheck.DIGITAL_SIGNATURE,
        ]:
            if checklist_signatures.get(check.value, False):
                passed.append(check.value)
                audit_log.append({"check": check.value, "status": "SIGNED"})
            else:
                failed.append(check.value)
                audit_log.append({"check": check.value, "status": "UNSIGNED"})
        
        can_submit = len(failed) == 0
        
        result = SubmissionResult(
            can_submit=can_submit,
            passed_checks=passed,
            failed_checks=failed,
            blocking_reason=f"Failed checks: {', '.join(failed)}" if failed else None,
            audit_trail={
                "validated_at": datetime.now(UTC).isoformat(),
                "bid_id": str(bid_id),
                "company_id": str(company_id),
                "checks": audit_log,
                "version": "1.0-submission-gate"
            }
        )
        
        logger.info(
            "submission_validation_completed",
            bid_id=str(bid_id),
            can_submit=can_submit,
            passed=len(passed),
            failed=len(failed),
            trace_id=trace_id
        )
        
        return result
