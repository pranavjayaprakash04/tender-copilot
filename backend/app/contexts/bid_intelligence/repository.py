"""Bid intelligence repository."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.tender_discovery.models import Tender
from app.shared.logger import get_logger

logger = get_logger()


class BidIntelligenceRepository:
    """Repository for bid intelligence data access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_tender_by_id(self, tender_id: UUID, company_id: UUID) -> Tender | None:
        """Get tender by ID scoped by company ID."""
        try:
            stmt = select(Tender).where(
                Tender.id == tender_id,
                Tender.company_id == company_id
            )
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                "get_tender_by_id_error",
                tender_id=str(tender_id),
                company_id=str(company_id),
                error=str(e)
            )
            raise

    async def get_bid_outcomes(self, company_id: UUID, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch bid outcomes for win probability training data."""
        try:
            # Query bid_outcomes table for historical data
            stmt = text("""
                SELECT
                    tender_id,
                    company_id,
                    bid_amount,
                    outcome_status,
                    loss_reason,
                    created_at
                FROM bid_outcomes
                WHERE company_id = :company_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)

            result = await self._session.execute(
                stmt,
                {"company_id": str(company_id), "limit": limit}
            )

            # Convert to list of dicts
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

        except Exception as e:
            logger.error(
                "get_bid_outcomes_error",
                company_id=str(company_id),
                limit=limit,
                error=str(e)
            )
            raise

    async def get_market_prices(self, category: str, state: str) -> list[dict[str, Any]]:
        """Fetch market prices from materialized view."""
        try:
            # Query market_prices materialized view
            result = await self._session.execute(
                text("""
                    SELECT
                        tender_category,
                        portal,
                        avg_estimated_value,
                        min_value,
                        max_value,
                        sample_count,
                        last_refreshed
                    FROM market_prices
                    WHERE tender_category = :category
                    ORDER BY sample_count DESC
                """),
                {"category": category}
            )

            # Convert to list of dicts
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

        except Exception as e:
            logger.error(
                "get_market_prices_error",
                category=category,
                error=str(e)
            )
            raise

    async def save_analysis_result(
        self,
        tender_id: UUID,
        company_id: UUID,
        analysis_type: str,
        result_json: dict[str, Any]
    ) -> None:
        """Save analysis result to database."""
        try:
            # Insert into bid_analysis_results table
            stmt = text("""
                INSERT INTO bid_analysis_results
                (tender_id, company_id, analysis_type, result_json, created_at)
                VALUES
                (:tender_id, :company_id, :analysis_type, :result_json, NOW())
            """)

            await self._session.execute(
                stmt,
                {
                    "tender_id": str(tender_id),
                    "company_id": str(company_id),
                    "analysis_type": analysis_type,
                    "result_json": result_json
                }
            )

            await self._session.commit()

            logger.info(
                "analysis_result_saved",
                tender_id=str(tender_id),
                company_id=str(company_id),
                analysis_type=analysis_type
            )

        except Exception as e:
            await self._session.rollback()
            logger.error(
                "save_analysis_result_error",
                tender_id=str(tender_id),
                company_id=str(company_id),
                analysis_type=analysis_type,
                error=str(e)
            )
            raise
