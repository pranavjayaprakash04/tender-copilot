from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, dict
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
from app.contexts.bid_generation.schemas import (
    BidGenerationCreate,
)
from app.contexts.tender_discovery.repository import TenderRepository
from app.infrastructure.groq_client import GroqClient, GroqModel
from app.shared.exceptions import NotFoundException, ValidationException
from app.shared.lang_context import LangContext

logger = structlog.get_logger()


class BidGenerationService:
    """Service for AI-powered bid generation."""

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
        # Validate tender exists and belongs to company
        tender = await self._tender_repo.get_by_id(tender_id, company_id)
        if not tender:
            raise NotFoundException("Tender not found")

        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Set default bid title if not provided
        if not bid_title:
            bid_title = f"Bid for {tender.title}"

        # Create bid generation record
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

    async def get_bid_generation_status(
        self,
        task_id: str,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidGeneration:
        """Get the status of a bid generation task."""
        bid_generation = await self._bid_repo.get_by_task_id(task_id, company_id)

        if not bid_generation:
            raise NotFoundException("Bid generation task not found")

        logger.info(
            "bid_generation_status_retrieved",
            trace_id=trace_id,
            task_id=task_id,
            status=bid_generation.status,
            progress=self._calculate_progress(bid_generation)
        )

        return bid_generation

    async def generate_bid_content(
        self,
        task_id: str,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidGeneration:
        """Generate bid content using AI (called by Celery task)."""
        bid_generation = await self._bid_repo.get_by_task_id(task_id, company_id)

        if not bid_generation:
            raise NotFoundException("Bid generation task not found")

        # Update status to generating
        await self._bid_repo.update_status(
            bid_generation.id, BidStatus.GENERATING, trace_id
        )

        try:
            # Get tender information
            tender = await self._tender_repo.get_by_id(bid_generation.tender_id, company_id)

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
                tender_id=bid_generation.tender_id,
                processing_time_ms=generated_content.get("processing_time_ms"),
                confidence_score=generated_content.get("confidence_score")
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

    async def _generate_bid_with_ai(
        self,
        tender: Any,
        bid_generation: BidGeneration,
        template: BidTemplate | None,
        trace_id: str | None = None
    ) -> dict[str, Any]:
        """Generate bid content using Groq AI."""
        start_time = datetime.utcnow()

        # Prepare tender context
        tender_context = self._prepare_tender_context(tender)

        # Get bid generation prompt based on type and language
        prompt = self._get_bid_generation_prompt(
            bid_generation.bid_type, bid_generation.language
        )

        # Create user prompt
        user_prompt = f"""
Tender Information:
{tender_context}

Bid Type: {bid_generation.bid_type}
Language: {bid_generation.language}
Bid Title: {bid_generation.bid_title}

{prompt}
"""

        try:
            # Call Groq for bid generation
            from app.prompts.bid_generation.bid_draft_v1 import BidDraftOutput

            result = await self._groq.complete(
                model=GroqModel.PRIMARY,  # Use llama-3.3-70b-versatile for quality bid generation
                system_prompt=self._get_system_prompt(),
                user_prompt=user_prompt,
                output_schema=BidDraftOutput,
                lang=LangContext.from_lang(bid_generation.language),
                trace_id=trace_id or f"bid-gen-{bid_generation.id}",
                company_id=str(bid_generation.company_id),
                temperature=0.7  # Higher temperature for creative bid content
            )

            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Convert to dict for storage
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

        # Add CPV codes if available
        if hasattr(tender, 'cpv_codes') and tender.cpv_codes:
            context += f"\nCPV Codes: {', '.join(tender.cpv_codes)}"

        return context.strip()

    def _get_bid_generation_prompt(self, bid_type: BidType, language: str) -> str:
        """Get appropriate prompt based on bid type and language."""
        if language == "ta":
            return self._get_tamil_prompt(bid_type)
        return self._get_english_prompt(bid_type)

    def _get_english_prompt(self, bid_type: BidType) -> str:
        """Get English prompt for bid generation."""
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

Ensure the proposal is competitive yet profitable, with clear financial justifications.
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

Ensure the proposal presents a cohesive solution that addresses all tender requirements.
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

Ensure the proposal demonstrates capability and suitability for the tender.
"""
        }

        return prompts.get(bid_type, prompts[BidType.TECHNICAL])

    def _get_tamil_prompt(self, bid_type: BidType) -> str:
        """Get Tamil prompt for bid generation."""
        base_prompt = """
தமிழில் ஒரு தொழில்முறை ஒப்பந்தங்கள் முன்மொழிலை உருவாக்கவும். பின்வருவனவற்றை உள்ளடக்க வேண்டும்:

1. சுயாதீனங்கள்
2. தொழில்நுட்ப அணுகுமுறை மற்றும் முறையான கருத்துக்கள்
3. செயல்பாட்டு திட்டம்
4. வள ஒதுக்கீடு
5. தர உத்தரவாதங்கள்
6. ஆபத்து குறைப்பு உத்திகள்
7. இணக்கத்தன்மை அணி
8. காலக்கெடு மற்றும் மைல்கக்கற்கள்

முன்மொழி தொழில்முறையாக, விரிவாக, மற்றும் ஒப்பந்தத் தேவைகளுக்கு ஏற்றதாக இருக்க வேண்டும்.
"""
        return base_prompt

    def _get_system_prompt(self) -> str:
        """Get system prompt for bid generation."""
        return """You are an expert bid proposal writer specializing in government tenders for Indian businesses. Your expertise includes:

- Indian public procurement processes
- Technical and financial bid preparation
- Compliance requirements and regulations
- Competitive bidding strategies
- MSME-specific advantages and considerations

Generate professional, compelling, and compliant bid proposals that maximize the chances of winning while maintaining profitability and quality standards."""

    def _calculate_progress(self, bid_generation: BidGeneration) -> float:
        """Calculate progress percentage for bid generation."""
        if bid_generation.status == BidStatus.PENDING:
            return 0.0
        elif bid_generation.status == BidStatus.GENERATING:
            return 50.0
        elif bid_generation.status == BidStatus.COMPLETED:
            return 100.0
        elif bid_generation.status == BidStatus.FAILED:
            return 0.0
        else:
            return 0.0

    async def _update_analytics(
        self,
        company_id: UUID,
        bid_generation: BidGeneration,
        success: bool,
        trace_id: str | None = None
    ) -> None:
        """Update bid generation analytics."""
        try:
            # Get or create today's analytics
            today = datetime.utcnow().date()
            period_start = datetime.combine(today, datetime.min.time())
            period_end = datetime.combine(today, datetime.max.time())

            analytics = await self._analytics_repo.get_period_analytics(
                company_id, period_start, period_end, "daily"
            )

            if not analytics:
                # Create new analytics record
                await self._analytics_repo.create_daily_analytics(company_id, today)
            else:
                # Update existing analytics
                await self._analytics_repo.update_analytics(
                    analytics.id, bid_generation, success
                )

        except Exception as e:
            logger.warning(
                "analytics_update_failed",
                trace_id=trace_id,
                company_id=company_id,
                error=str(e)
            )

    async def list_bid_generations(
        self,
        company_id: UUID,
        bid_type: BidType | None = None,
        status: BidStatus | None = None,
        page: int = 1,
        page_size: int = 20,
        trace_id: str | None = None
    ) -> tuple[list[BidGeneration], int]:
        """List bid generations with filters."""
        bid_generations, total = await self._bid_repo.list_by_company(
            company_id, bid_type, status, page, page_size
        )

        logger.info(
            "bid_generations_listed",
            trace_id=trace_id,
            company_id=company_id,
            count=len(bid_generations),
            total=total,
            bid_type=bid_type,
            status=status
        )

        return bid_generations, total

    async def cancel_bid_generation(
        self,
        task_id: str,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidGeneration:
        """Cancel a bid generation task."""
        bid_generation = await self._bid_repo.get_by_task_id(task_id, company_id)

        if not bid_generation:
            raise NotFoundException("Bid generation task not found")

        if bid_generation.status not in [BidStatus.PENDING, BidStatus.GENERATING]:
            raise ValidationException("Cannot cancel bid generation in current status")

        await self._bid_repo.update_status(
            bid_generation.id, BidStatus.CANCELLED, trace_id
        )

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
        """Retry a failed bid generation."""
        bid_generation = await self._bid_repo.get_by_task_id(task_id, company_id)

        if not bid_generation:
            raise NotFoundException("Bid generation task not found")

        if not bid_generation.can_retry:
            raise ValidationException("Cannot retry bid generation")

        # Reset status to pending and increment retry count
        await self._bid_repo.reset_for_retry(bid_generation.id, trace_id)

        logger.info(
            "bid_generation_retry_initiated",
            trace_id=trace_id,
            task_id=task_id,
            company_id=company_id,
            retry_count=bid_generation.retry_count + 1
        )

        return bid_generation
