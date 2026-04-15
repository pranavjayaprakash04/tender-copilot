# Add at top of file
from app.contexts.compliance_vault.compliance_engine import HardComplianceEngine, ComplianceException

# REPLACE the generate_bid_content method (around line 85) with this:
async def generate_bid_content(
    self,
    task_id: str,
    company_id: UUID,
    trace_id: str | None = None
) -> BidGeneration:
    """Generate bid content using AI - WITH COMPLIANCE GATE."""
    bid_generation = await self._bid_repo.get_by_task_id(task_id, company_id)

    if not bid_generation:
        raise NotFoundException("Bid generation task not found")

    # ⛔ STEP 1: HARD COMPLIANCE CHECK (CRITICAL FIX)
    compliance_engine = HardComplianceEngine(self._bid_repo._session)
    
    tender = await self._tender_repo.get_by_id(bid_generation.tender_id, company_id)
    if not tender:
        raise NotFoundException("Tender not found")
    
    compliance_result = await compliance_engine.validate_before_generation(
        company_id=company_id,
        tender=tender,
        bid_type=bid_generation.bid_type,
        trace_id=trace_id
    )
    
    # ⛔ STEP 2: BLOCK IF NOT COMPLIANT (DISQUALIFICATION PREVENTION)
    if not compliance_result.is_compliant:
        await self._bid_repo.update_with_compliance_failure(
            bid_generation.id,
            compliance_result,
            trace_id
        )
        
        missing_names = [m.value for m in compliance_result.missing_documents]
        expired_names = [e[0].value for e in compliance_result.expired_documents]
        
        logger.error(
            "bid_generation_blocked_compliance",
            trace_id=trace_id,
            missing=missing_names,
            expired=expired_names,
            audit=compliance_result.audit_trail
        )
        
        raise ComplianceException(
            message=f"🚫 COMPLIANCE FAILURE: Cannot generate bid.\n\n"
                   f"Missing documents: {', '.join(missing_names)}\n"
                   f"Expired documents: {', '.join(expired_names)}\n\n"
                   f"Upload required documents to Compliance Vault first.",
            missing_documents=compliance_result.missing_documents,
            expired_documents=compliance_result.expired_documents,
            audit_trail=compliance_result.audit_trail
        )
    
    # ✅ STEP 3: PROCEED TO AI GENERATION ONLY IF COMPLIANT
    await self._bid_repo.update_status(bid_generation.id, BidStatus.GENERATING)

    try:
        # Get template if specified
        template = None
        if bid_generation.template_used:
            template = await self._template_repo.get_by_id(
                UUID(bid_generation.template_used), company_id
            )

        # Generate bid content using AI
        generated_content = await self._generate_bid_with_ai(
            tender, bid_generation, template, trace_id
        )

        # Update bid generation with results
        updated_bid = await self._bid_repo.update_with_content(
            bid_generation.id, generated_content, trace_id
        )

        # Update analytics
        await self._update_analytics(company_id, bid_generation, True, trace_id)

        logger.info(
            "bid_generation_completed",
            trace_id=trace_id,
            task_id=task_id,
            tender_id=str(bid_generation.tender_id),
            compliance_validated=True  # Key tracking metric
        )

        return updated_bid

    except Exception as e:
        # Update status to failed
        await self._bid_repo.update_with_error(
            bid_generation.id, str(e), trace_id
        )

        # Update analytics
        await self._update_analytics(company_id, bid_generation, False, trace_id)

        logger.error(
            "bid_generation_failed",
            trace_id=trace_id,
            task_id=task_id,
            error=str(e)
        )

        raise
