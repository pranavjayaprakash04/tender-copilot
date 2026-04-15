from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog

from app.contexts.bid_generation.models import (
    BidGeneration,
    BidStatus,
    BidTemplate,
    BidType,
)
from app.contexts.bid_generation.repository import (
    BidGenerationAnalyticsRepository,
    BidGenerationRepository,
    BidTemplateRepository,
)
from app.contexts.bid_generation.schemas import BidGenerationCreate
from app.contexts.compliance_vault.compliance_engine import (
    ComplianceException,
    HardComplianceEngine,
)
from app.contexts.tender_discovery.repository import TenderRepository
from app.infrastructure.groq_client import GroqClient, GroqModel
from app.shared.exceptions import NotFoundException, ValidationException
from app.shared.lang_context import LangContext

logger = structlog.get_logger()


class BidGenerationService:
    """Service for AI-powered bid generation with COMPLIANCE GATE."""

    def __init__(
        self,
        bid_repo: BidGenerationRepository,
        template_repo: BidTemplateRepository,
        analytics_repo: BidGenerationAnalyticsRepository,
        tender_repo: TenderRepository,
        groq_client: GroqClient
    ) -> None:
        self._bid_repo = bid_repo
        self._template_repo = template_repo
        self._analytics_repo = analytics_repo
        self._tender_repo = tender_repo
        self._groq = groq_client

    async def initiate_bid_generation(
        self,
        tender_id: UUID,
        company_id: UUID,
        bid_type: BidType,
        language: str = "en",
        bid_title: str | None = None,
        bid_description: str | None = None,
        template_id: UUID | None = None,
        customization: dict[str, Any] | None = None,
        trace_id: str | None = None
    ) -> BidGeneration:
        """Initiate bid generation and return task ID immediately."""
        tender = await self._tender_repo.get_by_id(tender_id, company_id)
        if not tender:
            raise NotFoundException("Tender not found")

        task_id = str(uuid.uuid4())

        if not bid_title:
            bid_title = f"Bid for {tender.title}"

        bid_data = BidGenerationCreate(
            tender_id=tender_id,
            bid_type=bid_type,
            language=language,
            bid_title=bid_title,
            bid_description=bid_description,
            task_id=task_id,
            template_id=str(template_id) if template_id else None,
            customization_applied=bool(customization)
        )

        bid_generation = await self._bid_repo.create(bid_data)

        logger.info(
            "bid_generation_initiated",
            trace_id=trace_id,
            task_id=task_id,
            tender_id=tender_id,
            company_id=company_id,
            bid_type=bid_type,
            language=language
        )

        return bid_generation

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

        # ⛔ STEP 1: HARD COMPLIANCE CHECK (DISQUALIFICATION PREVENTION)
        compliance_engine = HardComplianceEngine(self._bid_repo._session)
        
        tender = await self._tender_repo.get_by_id(bid_generation.tender_id, company_id)
        if not tender:
            raise NotFoundException("Tender not found")
        
        compliance_result = await compliance_engine.validate_before_generation(
            company_id=company_id,
            tender_value=getattr(tender, 'tender_value', None),
            bid_type=bid_generation.bid_type,
            is_msme_preference=getattr(tender, 'msme_preference', False),
            trace_id=trace_id
        )
        
        # ⛔ STEP 2: BLOCK IF NOT COMPLIANT
        if not compliance_result.is_compliant:
            await self._bid_repo.update_status(bid_generation.id, "compliance_failed")
            
            missing_names = [m.value for m in compliance_result.missing_documents]
            expired_names = [e[0].value for e in compliance_result.expired_documents]
            
            logger.error(
                "bid_generation_blocked_compliance",
                trace_id=trace_id,
                task_id=task_id,
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
            template = None
            if bid_generation.template_used:
                template = await self._template_repo.get_by_id(
                    UUID(bid_generation.template_used), company_id
                )

            generated_content = await self._generate_bid_with_ai(
                tender, bid_generation, template, trace_id
            )

            updated_bid = await self._bid_repo.update_with_content(
                bid_generation.id, generated_content, trace_id
            )

            await self._update_analytics(company_id, bid_generation, True, trace_id)

            logger.info(
                "bid_generation_completed",
                trace_id=trace_id,
                task_id=task_id,
                tender_id=bid_generation.tender_id,
                compliance_validated=True
            )

            return updated_bid

        except Exception as e:
            await self._bid_repo.update_with_error(bid_generation.id, str(e), trace_id)
            await self._update_analytics(company_id, bid_generation, False, trace_id)

            logger.error(
                "bid_generation_failed",
                trace_id=trace_id,
                task_id=task_id,
                error=str(e)
            )
            raise

    async def _generate_bid_with_ai(
        self,
        tender: Any,
        bid_generation: BidGeneration,
        template: BidTemplate | None,
        trace_id: str | None = None
    ) -> dict[str, Any]:
        """Generate bid content using Groq AI."""
        start_time = datetime.now(UTC)

        tender_context = self._prepare_tender_context(tender)
        prompt = self._get_bid_generation_prompt(
            bid_generation.bid_type, bid_generation.language
        )

        user_prompt = f"""
Tender Information:
{tender_context}

Bid Type: {bid_generation.bid_type}
Language: {bid_generation.language}
Bid Title: {bid_generation.bid_title}

{prompt}
"""

        try:
            from app.prompts.bid_generation.bid_draft_v1 import BidDraftOutput

            result = await self._groq.complete(
                model=GroqModel.PRIMARY,
                system_prompt=self._get_system_prompt(),
                user_prompt=user_prompt,
                output_schema=BidDraftOutput,
                lang=LangContext.from_lang(bid_generation.language),
                trace_id=trace_id or f"bid-gen-{bid_generation.id}",
                company_id=str(bid_generation.company_id),
                temperature=0.7
            )

            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            content_dict = result.model_dump()
            content_dict["processing_time_ms"] = int(processing_time)

            return content_dict

        except Exception as e:
            logger.error(
                "ai_bid_generation_failed",
                trace_id=trace_id,
                bid_generation_id=bid_generation.id,
                error=str(e)
            )
            raise

    def _prepare_tender_context(self, tender: Any) -> str:
        """Prepare tender information for AI processing."""
        context = f"""
Title: {tender.title}
Description: {tender.description or 'N/A'}
Organization: {getattr(tender, 'organization_name', 'N/A')}
Tender Value: {getattr(tender, 'tender_value', 'N/A')}
EMD Amount: {getattr(tender, 'emd_amount', 'N/A')}
Bid Submission Deadline: {getattr(tender, 'bid_submission_deadline', 'N/A')}
Category: {getattr(tender, 'category', 'N/A')}
Sub-category: {getattr(tender, 'sub_category', 'N/A')}
"""

        if hasattr(tender, 'cpv_codes') and tender.cpv_codes:
            context += f"\nCPV Codes: {', '.join(tender.cpv_codes)}"

        return context.strip()

    def _get_bid_generation_prompt(self, bid_type: BidType, language: str) -> str:
        """Get appropriate prompt based on bid type and language."""
        if language == "ta":
            return self._get_tamil_prompt(bid_type)
        return self._get_english_prompt(bid_type)

    def _get_english_prompt(self, bid_type: BidType) -> str:
        prompts = {
            BidType.TECHNICAL: """
Generate a comprehensive technical bid proposal that includes:
1. Executive summary
2. Technical approach and methodology
3. Implementation plan
4. Resource allocation
5. Quality assurance measures
6. Risk mitigation strategies
7. Compliance matrix
8. Timeline and milestones

Ensure the proposal is professional, detailed, and tailored to the tender requirements.
""",
            BidType.FINANCIAL: """
Generate a detailed financial bid proposal that includes:
1. Cost breakdown structure
2. Pricing methodology
3. Payment terms and conditions
4. Financial guarantees
5. Cost optimization strategies
6. Value-added services
7. Return on investment analysis
8. Financial risk assessment

Ensure the proposal is competitive yet profitable.
""",
            BidType.COMBINED: """
Generate a comprehensive combined bid proposal that integrates both technical and financial aspects:
1. Executive summary
2. Technical approach and methodology
3. Implementation plan and timeline
4. Resource allocation and team structure
5. Cost breakdown and pricing strategy
6. Quality assurance and compliance
7. Risk management and mitigation
8. Value proposition and competitive advantages
""",
            BidType.QUALIFICATION: """
Generate a qualification bid proposal that includes:
1. Company profile and capabilities
2. Relevant experience and past projects
3. Technical expertise and resources
4. Financial stability and capacity
5. Compliance with requirements
6. Key personnel and qualifications
7. Certifications and accreditations
8. Competitive advantages
"""
        }
        return prompts.get(bid_type, prompts[BidType.TECHNICAL])

    def _get_tamil_prompt(self, bid_type: BidType) -> str:
        """Tamil prompt with proper business terminology."""
        base = """
தமிழில் ஒரு தொழில்முறை ஒப்பந்த முன்மொழிவை உருவாக்கவும். பின்வருவனவற்றை உள்ளடக்க வேண்டும்:

1. சுருக்கமான செயல்திட்டம் (Executive Summary)
2. தொழில்நுட்ப அணுகுமுறை மற்றும் முறையான கருத்துக்கள்
3. செயல்பாட்டு திட்டம்
4. வள ஒதுக்கீடு
5. தர உத்தரவாதங்கள்
6. ஆபத்து குறைப்பு உத்திகள்
7. இணக்கத்தன்மை அணி (Compliance Matrix)
8. காலக்கெடு மற்றும் மைல்கற்கள்

முக்கிய வழிகாட்டுதல்கள்:
- EMD = "பிணைத் தொகை" என்று பயன்படுத்தவும்
- GST = "வரி சேவை" (Goods and Services Tax)
- MSME = "சிறு குறு நடுத்தர நிறுவனங்கள்"
- "நாங்கள்" பதிலாக "எங்கள் நிறுவனம்" பயன்படுத்தவும்
- அரசு வார்த்தைகளை சரியாகப் பயன்படுத்தவும்
"""
        return base

    def _get_system_prompt(self) -> str:
        return """You are an expert bid proposal writer specializing in government tenders for Indian MSMEs. Your expertise includes:
- Indian public procurement processes (GeM, CPPP, State portals)
- Technical and financial bid preparation
- Compliance requirements (GST, PAN, EMD, OEM)
- MSME-specific advantages and reservations
- Tamil Nadu-specific tendering processes

Generate professional, compelling, and compliant bid proposals."""

    async def _update_analytics(
        self,
        company_id: UUID,
        bid_generation: BidGeneration,
        success: bool,
        trace_id: str | None = None
    ) -> None:
        try:
            from datetime import date
            today = date.today()
            
            analytics = await self._analytics_repo.get_period_analytics(
                company_id, datetime.combine(today, datetime.min.time()), 
                datetime.combine(today, datetime.max.time()), "daily"
            )

            if not analytics:
                await self._analytics_repo.create_daily_analytics(company_id, today)
            else:
                await self._analytics_repo.update_analytics(
                    analytics.id, bid_generation, success
                )

        except Exception as e:
            logger.warning("analytics_update_failed", trace_id=trace_id, error=str(e))

    async def get_bid_generation_status(
        self,
        task_id: str,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidGeneration:
        bid_generation = await self._bid_repo.get_by_task_id(task_id, company_id)

        if not bid_generation:
            raise NotFoundException("Bid generation task not found")

        logger.info(
            "bid_generation_status_retrieved",
            trace_id=trace_id,
            task_id=task_id,
            status=bid_generation.status
        )

        return bid_generation

    async def list_bid_generations(
        self,
        company_id: UUID,
        bid_type: BidType | None = None,
        status: BidStatus | None = None,
        page: int = 1,
        page_size: int = 20,
        trace_id: str | None = None
    ) -> tuple[list[BidGeneration], int]:
        bid_generations, total = await self._bid_repo.list_by_company(
            company_id, bid_type, status, page, page_size
        )

        logger.info(
            "bid_generations_listed",
            trace_id=trace_id,
            company_id=company_id,
            count=len(bid_generations),
            total=total
        )

        return bid_generations, total

    async def cancel_bid_generation(
        self,
        task_id: str,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidGeneration:
        bid_generation = await self._bid_repo.get_by_task_id(task_id, company_id)

        if not bid_generation:
            raise NotFoundException("Bid generation task not found")

        if bid_generation.status not in [BidStatus.PENDING, BidStatus.GENERATING]:
            raise ValidationException("Cannot cancel bid generation in current status")

        await self._bid_repo.update_status(bid_generation.id, BidStatus.CANCELLED, trace_id)

        logger.info(
            "bid_generation_cancelled",
            trace_id=trace_id,
            task_id=task_id,
            company_id=company_id
        )

        return bid_generation

    async def retry_failed_generation(
        self,
        task_id: str,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidGeneration:
        bid_generation = await self._bid_repo.get_by_task_id(task_id, company_id)

        if not bid_generation:
            raise NotFoundException("Bid generation task not found")

        if not bid_generation.can_retry:
            raise ValidationException("Cannot retry bid generation")

        await self._bid_repo.reset_for_retry(bid_generation.id, trace_id)

        logger.info(
            "bid_generation_retry_initiated",
            trace_id=trace_id,
            task_id=task_id,
            company_id=company_id,
            retry_count=bid_generation.retry_count + 1
        )

        return bid_generation
