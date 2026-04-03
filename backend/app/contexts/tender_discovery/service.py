from __future__ import annotations

from uuid import UUID

import structlog

from app.contexts.tender_discovery.repository import (
    TenderAlertRepository,
    TenderRepository,
    TenderSearchRepository,
)
from app.contexts.tender_discovery.schemas import (
    TenderAlertCreate,
    TenderAlertResponse,
    TenderAlertUpdate,
    TenderBulkDelete,
    TenderBulkUpdate,
    TenderClassificationRequest,
    TenderClassificationResponse,
    TenderCreate,
    TenderListResponse,
    TenderResponse,
    TenderSearchCreate,
    TenderSearchFilters,
    TenderSearchResponse,
    TenderSearchUpdate,
    TenderStatsResponse,
    TenderUpdate,
)
from app.infrastructure.groq_client import GroqClient, GroqModel
from app.prompts.tender.tender_classification_v1 import SYSTEM_PROMPT, build_prompt
from app.shared.exceptions import ValidationException
from app.shared.lang_context import LangContext

logger = structlog.get_logger()


class TenderDiscoveryService:
    """Service for tender discovery operations."""

    def __init__(
        self,
        tender_repo: TenderRepository,
        search_repo: TenderSearchRepository,
        alert_repo: TenderAlertRepository,
        groq_client: GroqClient,
    ) -> None:
        self._tender_repo = tender_repo
        self._search_repo = search_repo
        self._alert_repo = alert_repo
        self._groq = groq_client

    async def create_tender(
        self,
        tender_data: TenderCreate,
        trace_id: str | None = None
    ) -> TenderResponse:
        """Create a new tender."""
        try:
            tender = await self._tender_repo.create(tender_data)

            logger.info(
                "tender_created",
                trace_id=trace_id,
                tender_id=tender.id,
                company_id=tender.company_id,
                source=tender.source,
                title=tender.title
            )

            return TenderResponse.model_validate(tender)

        except Exception as e:
            logger.error(
                "tender_creation_failed",
                trace_id=trace_id,
                company_id=tender_data.company_id,
                source=tender_data.source,
                title=tender_data.title,
                error=str(e)
            )
            raise ValidationException(f"Failed to create tender: {e}")

    async def get_tender(
        self,
        tender_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> TenderResponse:
        """Get a tender by ID."""
        tender = await self._tender_repo.get_by_id(tender_id, company_id)

        logger.info(
            "tender_retrieved",
            trace_id=trace_id,
            tender_id=tender_id,
            company_id=company_id
        )

        return TenderResponse.model_validate(tender)

    async def list_tenders(
        self,
        company_id: UUID,
        filters: TenderSearchFilters | None = None,
        page: int = 1,
        page_size: int = 20,
        trace_id: str | None = None
    ) -> TenderListResponse:
        """List tenders for a company with filters."""
        tenders, total = await self._tender_repo.get_by_company(
            company_id, filters, page, page_size
        )

        logger.info(
            "tenders_listed",
            trace_id=trace_id,
            company_id=company_id,
            total=total,
            page=page,
            page_size=page_size
        )

        return TenderListResponse(
            tenders=[TenderResponse.model_validate(tender) for tender in tenders],
            total=total,
            page=page,
            page_size=page_size,
            has_next=page * page_size < total,
            has_previous=page > 1
        )

    async def update_tender(
        self,
        tender_id: UUID,
        company_id: UUID,
        update_data: TenderUpdate,
        trace_id: str | None = None
    ) -> TenderResponse:
        """Update a tender."""
        tender = await self._tender_repo.update(tender_id, company_id, update_data)

        logger.info(
            "tender_updated",
            trace_id=trace_id,
            tender_id=tender_id,
            company_id=company_id,
            updates=update_data.model_dump(exclude_unset=True)
        )

        return TenderResponse.model_validate(tender)

    async def delete_tender(
        self,
        tender_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> None:
        """Delete a tender."""
        await self._tender_repo.delete(tender_id, company_id)

        logger.info(
            "tender_deleted",
            trace_id=trace_id,
            tender_id=tender_id,
            company_id=company_id
        )

    async def get_bookmarked_tenders(
        self,
        company_id: UUID,
        page: int = 1,
        page_size: int = 20,
        trace_id: str | None = None
    ) -> TenderListResponse:
        """Get bookmarked tenders."""
        tenders, total = await self._tender_repo.get_bookmarked(company_id, page, page_size)

        logger.info(
            "bookmarked_tenders_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            total=total
        )

        return TenderListResponse(
            tenders=[TenderResponse.model_validate(tender) for tender in tenders],
            total=total,
            page=page,
            page_size=page_size,
            has_next=page * page_size < total,
            has_previous=page > 1
        )

    async def toggle_bookmark(
        self,
        tender_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> TenderResponse:
        """Toggle tender bookmark status."""
        tender = await self._tender_repo.get_by_id(tender_id, company_id)
        update_data = TenderUpdate(is_bookmarked=not tender.is_bookmarked)

        updated_tender = await self._tender_repo.update(tender_id, company_id, update_data)

        logger.info(
            "tender_bookmark_toggled",
            trace_id=trace_id,
            tender_id=tender_id,
            company_id=company_id,
            is_bookmarked=updated_tender.is_bookmarked
        )

        return TenderResponse.model_validate(updated_tender)

    async def get_closing_soon_tenders(
        self,
        company_id: UUID,
        days: int = 7,
        trace_id: str | None = None
    ) -> list[TenderResponse]:
        """Get tenders closing within specified days."""
        tenders = await self._tender_repo.get_closing_soon(company_id, days)

        logger.info(
            "closing_soon_tenders_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            days=days,
            count=len(tenders)
        )

        return [TenderResponse.model_validate(tender) for tender in tenders]

    async def get_urgent_tenders(
        self,
        company_id: UUID,
        trace_id: str | None = None
    ) -> list[TenderResponse]:
        """Get urgent tenders (closing within 3 days)."""
        tenders = await self._tender_repo.get_urgent(company_id)

        logger.info(
            "urgent_tenders_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            count=len(tenders)
        )

        return [TenderResponse.model_validate(tender) for tender in tenders]

    async def get_tender_stats(
        self,
        company_id: UUID,
        trace_id: str | None = None
    ) -> TenderStatsResponse:
        """Get tender statistics for a company."""
        stats = await self._tender_repo.get_stats(company_id)

        logger.info(
            "tender_stats_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            total_tenders=stats["total_tenders"]
        )

        return TenderStatsResponse(**stats)

    async def bulk_update_tenders(
        self,
        bulk_data: TenderBulkUpdate,
        company_id: UUID,
        trace_id: str | None = None
    ) -> list[TenderResponse]:
        """Bulk update tenders."""
        tenders = await self._tender_repo.bulk_update(
            bulk_data.tender_ids, company_id, bulk_data.updates
        )

        logger.info(
            "tenders_bulk_updated",
            trace_id=trace_id,
            company_id=company_id,
            tender_count=len(tenders)
        )

        return [TenderResponse.model_validate(tender) for tender in tenders]

    async def bulk_delete_tenders(
        self,
        bulk_data: TenderBulkDelete,
        company_id: UUID,
        trace_id: str | None = None
    ) -> None:
        """Bulk delete tenders."""
        await self._tender_repo.bulk_delete(bulk_data.tender_ids, company_id)

        logger.info(
            "tenders_bulk_deleted",
            trace_id=trace_id,
            company_id=company_id,
            tender_count=len(bulk_data.tender_ids)
        )

    async def classify_tender(
        self,
        request: TenderClassificationRequest,
        lang: LangContext = LangContext.from_lang("en"),
        trace_id: str | None = None,
        company_id: str | None = None
    ) -> TenderClassificationResponse:
        """Classify a tender using AI."""
        try:
            # Build prompt for tender classification
            user_prompt = build_prompt(
                request.title,
                request.description,
                request.procuring_entity,
                request.estimated_value
            )

            # Call Groq for classification
            from app.prompts.tender.tender_classification_v1 import ClassificationOutput

            result = await self._groq.complete(
                model=GroqModel.FAST,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                output_schema=ClassificationOutput,
                lang=lang,
                trace_id=trace_id,
                company_id=company_id,
                temperature=0.3
            )

            logger.info(
                "tender_classified",
                trace_id=trace_id,
                title=request.title,
                category=result.category,
                confidence=result.confidence
            )

            return TenderClassificationResponse(
                category=result.category,
                subcategory=result.subcategory,
                priority=result.priority,
                confidence=result.confidence,
                reasoning=result.reasoning
            )

        except Exception as e:
            logger.error(
                "tender_classification_failed",
                trace_id=trace_id,
                title=request.title,
                error=str(e)
            )
            raise ValidationException(f"Failed to classify tender: {e}")

    # Search Management
    async def create_search(
        self,
        search_data: TenderSearchCreate,
        company_id: UUID,
        trace_id: str | None = None
    ) -> TenderSearchResponse:
        """Create a new search."""
        search_data.company_id = company_id
        search = await self._search_repo.create(search_data)

        logger.info(
            "search_created",
            trace_id=trace_id,
            search_id=search.id,
            company_id=company_id,
            is_saved=search.is_saved_search
        )

        return TenderSearchResponse.model_validate(search)

    async def get_searches(
        self,
        company_id: UUID,
        saved_only: bool = False,
        trace_id: str | None = None
    ) -> list[TenderSearchResponse]:
        """Get searches for a company."""
        searches = await self._search_repo.get_by_company(company_id, saved_only)

        logger.info(
            "searches_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            saved_only=saved_only,
            count=len(searches)
        )

        return [TenderSearchResponse.model_validate(search) for search in searches]

    async def update_search(
        self,
        search_id: UUID,
        company_id: UUID,
        update_data: TenderSearchUpdate,
        trace_id: str | None = None
    ) -> TenderSearchResponse:
        """Update a search."""
        search = await self._search_repo.update(search_id, company_id, update_data)

        logger.info(
            "search_updated",
            trace_id=trace_id,
            search_id=search_id,
            company_id=company_id
        )

        return TenderSearchResponse.model_validate(search)

    async def delete_search(
        self,
        search_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> None:
        """Delete a search."""
        await self._search_repo.delete(search_id, company_id)

        logger.info(
            "search_deleted",
            trace_id=trace_id,
            search_id=search_id,
            company_id=company_id
        )

    async def run_saved_search(
        self,
        search_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> TenderListResponse:
        """Run a saved search and return results."""
        search = await self._search_repo.get_by_id(search_id, company_id)

        # Build filters from search
        filters = TenderSearchFilters(
            search_query=search.search_query,
            category=search.category,
            min_value=search.min_value,
            max_value=search.max_value,
            state=search.state,
            source=search.source
        )

        # Get tenders matching filters
        tenders, total = await self._tender_repo.get_by_company(company_id, filters)

        # Update search run stats
        await self._search_repo.update_run_stats(search_id)

        logger.info(
            "saved_search_run",
            trace_id=trace_id,
            search_id=search_id,
            company_id=company_id,
            results_count=len(tenders)
        )

        return TenderListResponse(
            tenders=[TenderResponse.model_validate(tender) for tender in tenders],
            total=total,
            page=1,
            page_size=len(tenders),
            has_next=False,
            has_previous=False
        )

    # Alert Management
    async def create_alert(
        self,
        alert_data: TenderAlertCreate,
        company_id: UUID,
        trace_id: str | None = None
    ) -> TenderAlertResponse:
        """Create a new alert."""
        alert_data.company_id = company_id
        alert = await self._alert_repo.create(alert_data)

        logger.info(
            "alert_created",
            trace_id=trace_id,
            alert_id=alert.id,
            company_id=company_id,
            alert_type=alert.alert_type
        )

        return TenderAlertResponse.model_validate(alert)

    async def get_alerts(
        self,
        company_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        trace_id: str | None = None
    ) -> list[TenderAlertResponse]:
        """Get alerts for a company."""
        alerts = await self._alert_repo.get_by_company(company_id, unread_only, limit)

        logger.info(
            "alerts_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            unread_only=unread_only,
            count=len(alerts)
        )

        return [TenderAlertResponse.model_validate(alert) for alert in alerts]

    async def update_alert(
        self,
        alert_id: UUID,
        company_id: UUID,
        update_data: TenderAlertUpdate,
        trace_id: str | None = None
    ) -> TenderAlertResponse:
        """Update an alert."""
        alert = await self._alert_repo.update(alert_id, company_id, update_data)

        logger.info(
            "alert_updated",
            trace_id=trace_id,
            alert_id=alert_id,
            company_id=company_id,
            is_read=alert.is_read
        )

        return TenderAlertResponse.model_validate(alert)

    async def mark_all_alerts_read(
        self,
        company_id: UUID,
        trace_id: str | None = None
    ) -> int:
        """Mark all alerts as read for a company."""
        count = await self._alert_repo.mark_all_read(company_id)

        logger.info(
            "alerts_marked_read",
            trace_id=trace_id,
            company_id=company_id,
            count=count
        )

        return count

    async def delete_alert(
        self,
        alert_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> None:
        """Delete an alert."""
        await self._alert_repo.delete(alert_id, company_id)

        logger.info(
            "alert_deleted",
            trace_id=trace_id,
            alert_id=alert_id,
            company_id=company_id
        )

    async def get_unread_alerts_count(
        self,
        company_id: UUID,
        trace_id: str | None = None
    ) -> int:
        """Get count of unread alerts for a company."""
        count = await self._alert_repo.get_unread_count(company_id)

        logger.info(
            "unread_alerts_count_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            count=count
        )

        return count

    async def create_deadline_alerts(
        self,
        company_id: UUID,
        trace_id: str | None = None
    ) -> int:
        """Create alerts for tenders approaching deadline."""
        # Get tenders closing in 3 days
        urgent_tenders = await self._tender_repo.get_closing_soon(company_id, days=3)

        alerts_created = 0
        for tender in urgent_tenders:
            # Check if alert already exists
            existing_alerts = await self._alert_repo.get_by_company(company_id)

            alert_exists = any(
                alert.tender_id == tender.id and alert.alert_type == "deadline_reminder"
                for alert in existing_alerts
            )

            if not alert_exists:
                alert_data = TenderAlertCreate(
                    tender_id=tender.id,
                    alert_type="deadline_reminder",
                    message=f"Tender '{tender.title}' is closing on {tender.bid_submission_deadline.strftime('%Y-%m-%d')}. Only {tender.days_until_deadline} days left!"
                )

                await self._alert_repo.create(alert_data)
                alerts_created += 1

        logger.info(
            "deadline_alerts_created",
            trace_id=trace_id,
            company_id=company_id,
            alerts_created=alerts_created
        )

        return alerts_created
