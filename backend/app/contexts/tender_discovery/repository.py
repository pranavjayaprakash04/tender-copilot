from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session

from app.contexts.tender_discovery.models import Tender, TenderAlert, TenderSearch
from app.contexts.tender_discovery.schemas import (
    TenderAlertCreate,
    TenderAlertUpdate,
    TenderCreate,
    TenderSearchCreate,
    TenderSearchFilters,
    TenderSearchUpdate,
    TenderUpdate,
)
from app.shared.exceptions import NotFoundException, ValidationException


class TenderRepository:
    """Repository for Tender operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def create(self, tender_data: TenderCreate) -> Tender:
        """Create a new tender."""
        # Check if tender with same ID already exists for this company
        existing = await self._session.execute(
            select(Tender).where(
                and_(
                    Tender.company_id == tender_data.company_id,
                    Tender.tender_id == tender_data.tender_id,
                    Tender.source == tender_data.source
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationException("Tender with this ID already exists for this company")

        tender = Tender(**tender_data.model_dump())
        self._session.add(tender)
        await self._session.commit()
        await self._session.refresh(tender)
        return tender

    async def get_by_id(self, tender_id: UUID, company_id: UUID) -> Tender:
        """Get tender by ID."""
        result = await self._session.execute(
            select(Tender).where(
                and_(Tender.id == tender_id, Tender.company_id == company_id)
            )
        )
        tender = result.scalar_one_or_none()
        if not tender:
            raise NotFoundException("Tender not found")
        return tender

    async def get_by_tender_id(self, tender_id: str, source: str, company_id: UUID) -> Tender:
        """Get tender by original tender ID and source."""
        result = await self._session.execute(
            select(Tender).where(
                and_(
                    Tender.tender_id == tender_id,
                    Tender.source == source,
                    Tender.company_id == company_id
                )
            )
        )
        tender = result.scalar_one_or_none()
        if not tender:
            raise NotFoundException("Tender not found")
        return tender

    async def get_by_company(
        self,
        company_id: UUID,
        filters: TenderSearchFilters | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Tender], int]:
        """Get tenders for a company with filters and pagination."""
        query = select(Tender).where(Tender.company_id == company_id)

        # Apply filters
        if filters:
            conditions = []

            if filters.search_query:
                conditions.append(
                    or_(
                        Tender.title.ilike(f"%{filters.search_query}%"),
                        Tender.description.ilike(f"%{filters.search_query}%"),
                        Tender.procuring_entity.ilike(f"%{filters.search_query}%")
                    )
                )

            if filters.category:
                conditions.append(Tender.category == filters.category)

            if filters.min_value:
                conditions.append(Tender.estimated_value >= filters.min_value)

            if filters.max_value:
                conditions.append(Tender.estimated_value <= filters.max_value)

            if filters.state:
                conditions.append(Tender.state == filters.state)

            if filters.source:
                conditions.append(Tender.source == filters.source)

            if filters.status:
                conditions.append(Tender.status == filters.status)

            if filters.priority:
                conditions.append(Tender.priority == filters.priority)

            if filters.is_bookmarked is not None:
                conditions.append(Tender.is_bookmarked == filters.is_bookmarked)

            if filters.is_active is not None:
                conditions.append(Tender.is_active == filters.is_active)

            if filters.deadline_days:
                deadline_threshold = datetime.utcnow() + timedelta(days=filters.deadline_days)
                conditions.append(
                    and_(
                        Tender.bid_submission_deadline <= deadline_threshold,
                        Tender.bid_submission_deadline >= datetime.utcnow(),
                        Tender.status.in_([Tender.Status.PUBLISHED, Tender.Status.BID_SUBMISSION_OPEN])
                    )
                )

            if filters.date_from:
                conditions.append(Tender.published_date >= filters.date_from)

            if filters.date_to:
                conditions.append(Tender.published_date <= filters.date_to)

            if conditions:
                query = query.where(and_(*conditions))

        # Order by published date descending
        query = query.order_by(desc(Tender.published_date))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self._session.execute(query)
        tenders = list(result.scalars().all())

        return tenders, total

    async def update(self, tender_id: UUID, company_id: UUID, update_data: TenderUpdate) -> Tender:
        """Update a tender."""
        tender = await self.get_by_id(tender_id, company_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(tender, field, value)

        tender.last_updated = datetime.utcnow()
        await self._session.commit()
        await self._session.refresh(tender)
        return tender

    async def delete(self, tender_id: UUID, company_id: UUID) -> None:
        """Delete a tender."""
        tender = await self.get_by_id(tender_id, company_id)
        await self._session.delete(tender)
        await self._session.commit()

    async def get_bookmarked(self, company_id: UUID, page: int = 1, page_size: int = 20) -> tuple[list[Tender], int]:
        """Get bookmarked tenders."""
        query = select(Tender).where(
            and_(Tender.company_id == company_id, Tender.is_bookmarked)
        ).order_by(desc(Tender.published_date))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self._session.execute(query)
        tenders = list(result.scalars().all())

        return tenders, total

    async def get_closing_soon(self, company_id: UUID, days: int = 7) -> list[Tender]:
        """Get tenders closing within specified days."""
        deadline_threshold = datetime.utcnow() + timedelta(days=days)

        result = await self._session.execute(
            select(Tender).where(
                and_(
                    Tender.company_id == company_id,
                    Tender.bid_submission_deadline <= deadline_threshold,
                    Tender.bid_submission_deadline >= datetime.utcnow(),
                    Tender.status.in_([Tender.Status.PUBLISHED, Tender.Status.BID_SUBMISSION_OPEN]),
                    Tender.is_active
                )
            ).order_by(Tender.bid_submission_deadline)
        )

        return list(result.scalars().all())

    async def get_urgent(self, company_id: UUID) -> list[Tender]:
        """Get urgent tenders (closing within 3 days)."""
        return await self.get_closing_soon(company_id, days=3)

    async def get_stats(self, company_id: UUID) -> dict:
        """Get tender statistics for a company."""
        # Total tenders
        total_result = await self._session.execute(
            select(func.count(Tender.id)).where(Tender.company_id == company_id)
        )
        total = total_result.scalar()

        # Active tenders
        active_result = await self._session.execute(
            select(func.count(Tender.id)).where(
                and_(
                    Tender.company_id == company_id,
                    Tender.is_active,
                    Tender.status.in_([Tender.Status.PUBLISHED, Tender.Status.BID_SUBMISSION_OPEN])
                )
            )
        )
        active = active_result.scalar()

        # Bookmarked tenders
        bookmarked_result = await self._session.execute(
            select(func.count(Tender.id)).where(
                and_(Tender.company_id == company_id, Tender.is_bookmarked)
            )
        )
        bookmarked = bookmarked_result.scalar()

        # Closing soon (7 days)
        deadline_threshold = datetime.utcnow() + timedelta(days=7)
        closing_soon_result = await self._session.execute(
            select(func.count(Tender.id)).where(
                and_(
                    Tender.company_id == company_id,
                    Tender.bid_submission_deadline <= deadline_threshold,
                    Tender.bid_submission_deadline >= datetime.utcnow(),
                    Tender.status.in_([Tender.Status.PUBLISHED, Tender.Status.BID_SUBMISSION_OPEN])
                )
            )
        )
        closing_soon = closing_soon_result.scalar()

        # Urgent (3 days)
        urgent_threshold = datetime.utcnow() + timedelta(days=3)
        urgent_result = await self._session.execute(
            select(func.count(Tender.id)).where(
                and_(
                    Tender.company_id == company_id,
                    Tender.bid_submission_deadline <= urgent_threshold,
                    Tender.bid_submission_deadline >= datetime.utcnow(),
                    Tender.status.in_([Tender.Status.PUBLISHED, Tender.Status.BID_SUBMISSION_OPEN])
                )
            )
        )
        urgent = urgent_result.scalar()

        # By category
        by_category_result = await self._session.execute(
            select(Tender.category, func.count(Tender.id))
            .where(and_(Tender.company_id == company_id, Tender.is_active))
            .group_by(Tender.category)
        )
        by_category = dict(by_category_result.all())

        # By source
        by_source_result = await self._session.execute(
            select(Tender.source, func.count(Tender.id))
            .where(and_(Tender.company_id == company_id, Tender.is_active))
            .group_by(Tender.source)
        )
        by_source = dict(by_source_result.all())

        # By status
        by_status_result = await self._session.execute(
            select(Tender.status, func.count(Tender.id))
            .where(Tender.company_id == company_id)
            .group_by(Tender.status)
        )
        by_status = dict(by_status_result.all())

        # Total estimated value
        value_result = await self._session.execute(
            select(func.sum(Tender.estimated_value))
            .where(
                and_(
                    Tender.company_id == company_id,
                    Tender.estimated_value.is_not(None),
                    Tender.is_active
                )
            )
        )
        total_value = value_result.scalar()

        return {
            "total_tenders": total,
            "active_tenders": active,
            "bookmarked_tenders": bookmarked,
            "closing_soon": closing_soon,
            "urgent": urgent,
            "by_category": by_category,
            "by_source": by_source,
            "by_status": by_status,
            "total_estimated_value": float(total_value) if total_value else None
        }

    async def bulk_update(self, tender_ids: list[UUID], company_id: UUID, update_data: TenderUpdate) -> list[Tender]:
        """Bulk update tenders."""
        # Verify all tenders belong to the company
        result = await self._session.execute(
            select(Tender).where(
                and_(
                    Tender.id.in_(tender_ids),
                    Tender.company_id == company_id
                )
            )
        )
        tenders = list(result.scalars().all())

        if len(tenders) != len(tender_ids):
            raise ValidationException("Some tenders not found or don't belong to this company")

        update_dict = update_data.model_dump(exclude_unset=True)
        for tender in tenders:
            for field, value in update_dict.items():
                setattr(tender, field, value)
            tender.last_updated = datetime.utcnow()

        await self._session.commit()
        return tenders

    async def bulk_delete(self, tender_ids: list[UUID], company_id: UUID) -> None:
        """Bulk delete tenders."""
        # Verify all tenders belong to the company
        result = await self._session.execute(
            select(Tender).where(
                and_(
                    Tender.id.in_(tender_ids),
                    Tender.company_id == company_id
                )
            )
        )
        tenders = list(result.scalars().all())

        if len(tenders) != len(tender_ids):
            raise ValidationException("Some tenders not found or don't belong to this company")

        for tender in tenders:
            await self._session.delete(tender)

        await self._session.commit()


class TenderSearchRepository:
    """Repository for TenderSearch operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def create(self, search_data: TenderSearchCreate) -> TenderSearch:
        """Create a new search."""
        search = TenderSearch(**search_data.model_dump())
        self._session.add(search)
        await self._session.commit()
        await self._session.refresh(search)
        return search

    async def get_by_id(self, search_id: UUID, company_id: UUID) -> TenderSearch:
        """Get search by ID."""
        result = await self._session.execute(
            select(TenderSearch).where(
                and_(TenderSearch.id == search_id, TenderSearch.company_id == company_id)
            )
        )
        search = result.scalar_one_or_none()
        if not search:
            raise NotFoundException("Search not found")
        return search

    async def get_by_company(self, company_id: UUID, saved_only: bool = False) -> list[TenderSearch]:
        """Get searches for a company."""
        query = select(TenderSearch).where(TenderSearch.company_id == company_id)

        if saved_only:
            query = query.where(TenderSearch.is_saved_search)

        query = query.order_by(desc(TenderSearch.created_at))

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update(self, search_id: UUID, company_id: UUID, update_data: TenderSearchUpdate) -> TenderSearch:
        """Update a search."""
        search = await self.get_by_id(search_id, company_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(search, field, value)

        await self._session.commit()
        await self._session.refresh(search)
        return search

    async def delete(self, search_id: UUID, company_id: UUID) -> None:
        """Delete a search."""
        search = await self.get_by_id(search_id, company_id)
        await self._session.delete(search)
        await self._session.commit()

    async def update_run_stats(self, search_id: UUID) -> None:
        """Update search run statistics."""
        search = await self._session.get(TenderSearch, search_id)
        if search:
            search.last_run = datetime.utcnow()
            search.run_count += 1
            await self._session.commit()


class TenderAlertRepository:
    """Repository for TenderAlert operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def create(self, alert_data: TenderAlertCreate) -> TenderAlert:
        """Create a new alert."""
        alert = TenderAlert(**alert_data.model_dump())
        self._session.add(alert)
        await self._session.commit()
        await self._session.refresh(alert)
        return alert

    async def get_by_id(self, alert_id: UUID, company_id: UUID) -> TenderAlert:
        """Get alert by ID."""
        result = await self._session.execute(
            select(TenderAlert).where(
                and_(TenderAlert.id == alert_id, TenderAlert.company_id == company_id)
            )
        )
        alert = result.scalar_one_or_none()
        if not alert:
            raise NotFoundException("Alert not found")
        return alert

    async def get_by_company(self, company_id: UUID, unread_only: bool = False, limit: int = 50) -> list[TenderAlert]:
        """Get alerts for a company."""
        query = select(TenderAlert).where(TenderAlert.company_id == company_id)

        if unread_only:
            query = query.where(TenderAlert.is_read.is_not(True))

        query = query.order_by(desc(TenderAlert.created_at)).limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update(self, alert_id: UUID, company_id: UUID, update_data: TenderAlertUpdate) -> TenderAlert:
        """Update an alert."""
        alert = await self.get_by_id(alert_id, company_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(alert, field, value)

        if update_data.is_read:
            alert.read_at = datetime.utcnow()

        await self._session.commit()
        await self._session.refresh(alert)
        return alert

    async def mark_all_read(self, company_id: UUID) -> int:
        """Mark all alerts as read for a company."""
        result = await self._session.execute(
            select(TenderAlert).where(
                and_(TenderAlert.company_id == company_id, TenderAlert.is_read.is_not(True))
            )
        )
        alerts = list(result.scalars().all())

        for alert in alerts:
            alert.is_read = True
            alert.read_at = datetime.utcnow()

        await self._session.commit()
        return len(alerts)

    async def delete(self, alert_id: UUID, company_id: UUID) -> None:
        """Delete an alert."""
        alert = await self.get_by_id(alert_id, company_id)
        await self._session.delete(alert)
        await self._session.commit()

    async def get_unread_count(self, company_id: UUID) -> int:
        """Get count of unread alerts for a company."""
        result = await self._session.execute(
            select(func.count(TenderAlert.id)).where(
                and_(TenderAlert.company_id == company_id, TenderAlert.is_read.is_not(True))
            )
        )
        return result.scalar()
