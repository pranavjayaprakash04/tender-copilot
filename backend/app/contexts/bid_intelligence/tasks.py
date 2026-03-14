"""Bid intelligence Celery tasks."""

from __future__ import annotations

from uuid import UUID

from app.database import get_async_session
from app.infrastructure.celery_app import shared_task
from app.infrastructure.groq_client import GroqClient
from app.shared.logger import get_logger

logger = get_logger()


@shared_task(name="refresh_market_prices_task")
def refresh_market_prices_task() -> None:
    """Refresh market prices materialized view (nightly Celery beat task)."""
    try:
        # Execute the materialized view refresh SQL
        refresh_sql = """
        REFRESH MATERIALIZED VIEW CONCURRENTLY market_prices;
        """

        # Use async session to execute the refresh
        async def execute_refresh():
            async for session in get_async_session():
                await session.execute(refresh_sql)
                await session.commit()
                logger.info("market_prices_view_refreshed")
                break

        import asyncio
        asyncio.run(execute_refresh())

    except Exception as e:
        logger.error("refresh_market_prices_error", error=str(e))
        raise


@shared_task(name="compute_win_probability_task")
def compute_win_probability_task(tender_id: str, company_id: str) -> None:
    """Compute win probability for a tender-company pair."""
    try:
        from app.contexts.bid_intelligence.repository import BidIntelligenceRepository
        from app.contexts.bid_intelligence.schemas import WinProbabilityRequest
        from app.contexts.bid_intelligence.service import BidIntelligenceService
        from app.contexts.company_profile.repository import CompanyProfileRepository
        from app.contexts.tender_discovery.repository import TenderRepository

        # Convert string IDs to UUID
        tender_uuid = UUID(tender_id)
        company_uuid = UUID(company_id)

        async def compute_probability():
            async for session in get_async_session():
                # Initialize repositories and service
                bid_repo = BidIntelligenceRepository(session)
                tender_repo = TenderRepository()
                company_repo = CompanyProfileRepository()
                groq_client = GroqClient()

                service = BidIntelligenceService(
                    groq_client=groq_client,
                    tender_repo=tender_repo,
                    company_repo=company_repo,
                    bid_lifecycle_session=session
                )

                # Fetch tender + company bid outcomes from repository
                tender = await tender_repo.get_by_id(tender_uuid, company_uuid)
                if not tender:
                    logger.warning(
                        "compute_win_probability_tender_not_found",
                        tender_id=tender_id,
                        company_id=company_id
                    )
                    return

                bid_outcomes = await bid_repo.get_bid_outcomes(company_uuid, limit=100)

                # Create request for win probability calculation
                request = WinProbabilityRequest(
                    tender_id=tender_uuid,
                    company_id=company_uuid,
                    our_bid_amount=None  # Will use market data only
                )

                # Call bid intelligence service to compute win probability
                result = await service.calculate_win_probability(request)

                # Store result via repository
                result_data = {
                    "win_probability": result.win_probability,
                    "confidence": result.confidence,
                    "factors": result.factors,
                    "market_avg": result.market_avg,
                    "recommended_range": result.recommended_range,
                    "bid_outcomes_count": len(bid_outcomes)
                }

                await bid_repo.save_analysis_result(
                    tender_id=tender_uuid,
                    company_id=company_uuid,
                    analysis_type="win_probability",
                    result_json=result_data
                )

                logger.info(
                    "win_probability_computed",
                    tender_id=tender_id,
                    company_id=company_id,
                    win_probability=result.win_probability
                )
                break

        import asyncio
        asyncio.run(compute_probability())

    except Exception as e:
        logger.error(
            "compute_win_probability_error",
            tender_id=tender_id,
            company_id=company_id,
            error=str(e)
        )
        raise


@shared_task(name="run_competitor_analysis_task")
def run_competitor_analysis_task(tender_id: str, company_id: str) -> None:
    """Run competitor analysis for a tender-company pair."""
    try:
        from app.contexts.bid_intelligence.repository import BidIntelligenceRepository
        from app.contexts.bid_intelligence.schemas import CompetitorAnalysisRequest
        from app.contexts.bid_intelligence.service import BidIntelligenceService
        from app.contexts.company_profile.repository import CompanyProfileRepository
        from app.contexts.tender_discovery.repository import TenderRepository

        # Convert string IDs to UUID
        tender_uuid = UUID(tender_id)
        company_uuid = UUID(company_id)

        async def run_analysis():
            async for session in get_async_session():
                # Initialize repositories and service
                bid_repo = BidIntelligenceRepository(session)
                tender_repo = TenderRepository()
                company_repo = CompanyProfileRepository()
                groq_client = GroqClient()

                service = BidIntelligenceService(
                    groq_client=groq_client,
                    tender_repo=tender_repo,
                    company_repo=company_repo,
                    bid_lifecycle_session=session
                )

                # Fetch tender details
                tender = await tender_repo.get_by_id(tender_uuid, company_uuid)
                if not tender:
                    logger.warning(
                        "competitor_analysis_tender_not_found",
                        tender_id=tender_id,
                        company_id=company_id
                    )
                    return

                # Create request for competitor analysis
                request = CompetitorAnalysisRequest(
                    tender_id=tender_uuid,
                    company_id=company_uuid,
                    lang="en"  # Default to English
                )

                # Call DeepSeek-R1 via Groq client for competitor analysis
                result = await service.analyze_competitors(request)

                # Store result via repository
                result_data = {
                    "insights": [
                        {
                            "competitor_name": insight.competitor_name,
                            "estimated_bid": insight.estimated_bid,
                            "win_probability": insight.win_probability,
                            "strengths": insight.strengths,
                            "weaknesses": insight.weaknesses
                        }
                        for insight in result.insights
                    ],
                    "our_win_probability": result.our_win_probability,
                    "recommended_price": result.recommended_price,
                    "analysis_lang": result.analysis_lang,
                    "generated_at": result.generated_at.isoformat()
                }

                await bid_repo.save_analysis_result(
                    tender_id=tender_uuid,
                    company_id=company_uuid,
                    analysis_type="competitor_analysis",
                    result_json=result_data
                )

                logger.info(
                    "competitor_analysis_completed",
                    tender_id=tender_id,
                    company_id=company_id,
                    insights_count=len(result.insights)
                )
                break

        import asyncio
        asyncio.run(run_analysis())

    except Exception as e:
        logger.error(
            "run_competitor_analysis_error",
            tender_id=tender_id,
            company_id=company_id,
            error=str(e)
        )
        raise
