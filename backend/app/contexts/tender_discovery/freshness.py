from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.tender_discovery.models import Tender

logger = structlog.get_logger()


class DataFreshness(StrEnum):
    FRESH = "fresh"        # < 1 hour (Green)
    STALE = "stale"        # 1-6 hours (Yellow)
    CRITICAL = "critical"  # 6-24 hours (Red)
    OFFLINE = "offline"    # > 24 hours (Don't show)


class TenderFreshnessService:
    """
    Track data freshness from your Supabase scraper.
    Shows warnings when data is stale.
    """
    
    THRESHOLDS = {
        DataFreshness.FRESH: timedelta(hours=1),
        DataFreshness.STALE: timedelta(hours=6),
        DataFreshness.CRITICAL: timedelta(hours=24),
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_freshness_status(self, tender_id: int | UUID) -> dict[str, Any]:
        """Get freshness status for a single tender."""
        stmt = select(Tender).where(Tender.id == tender_id)
        result = await self.session.execute(stmt)
        tender = result.scalar_one_or_none()
        
        if not tender:
            return {
                "status": DataFreshness.OFFLINE,
                "age_hours": None,
                "warning": "Tender not found",
                "color": "gray"
            }
        
        scraped_at = getattr(tender, 'scraped_at', None)
        if not scraped_at:
            return {
                "status": DataFreshness.OFFLINE,
                "age_hours": None,
                "warning": "No freshness data - verify on official portal",
                "color": "red",
                "data_source": getattr(tender, 'data_source', 'unknown')
            }
        
        age = datetime.now(UTC) - scraped_at
        age_hours = age.total_seconds() / 3600
        
        if age < self.THRESHOLDS[DataFreshness.FRESH]:
            status = DataFreshness.FRESH
            color = "green"
            warning = None
        elif age < self.THRESHOLDS[DataFreshness.STALE]:
            status = DataFreshness.STALE
            color = "yellow"
            warning = f"Data is {age_hours:.1f} hours old. Verify deadline on official portal."
        elif age < self.THRESHOLDS[DataFreshness.CRITICAL]:
            status = DataFreshness.CRITICAL
            color = "red"
            warning = f"WARNING: Data is {age_hours:.1f} hours old. Check GeM directly before proceeding."
        else:
            status = DataFreshness.OFFLINE
            color = "red"
            warning = "Data is >24 hours old. DO NOT TRUST DEADLINES. Visit gem.gov.in immediately."
        
        return {
            "status": status.value,
            "age_hours": round(age_hours, 1),
            "scraped_at": scraped_at.isoformat(),
            "data_source": getattr(tender, 'data_source', 'unknown'),
            "warning": warning,
            "color": color,
            "is_actionable": status in [DataFreshness.FRESH, DataFreshness.STALE]
        }
    
    async def get_dashboard_stats(self) -> dict[str, Any]:
        """Get freshness stats for monitoring dashboard."""
        stmt = select(Tender)
        result = await self.session.execute(stmt)
        tenders = result.scalars().all()
        
        total = len(tenders)
        if total == 0:
            return {
                "total": 0,
                "fresh": 0,
                "stale": 0,
                "critical": 0,
                "offline": 0,
                "health_score": 0,
                "last_updated": None
            }
        
        fresh = 0
        stale = 0
        critical = 0
        offline = 0
        last_updated = None
        
        for t in tenders:
            scraped = getattr(t, 'scraped_at', None)
            if scraped:
                if not last_updated or scraped > last_updated:
                    last_updated = scraped
                
                age = datetime.now(UTC) - scraped
                if age < self.THRESHOLDS[DataFreshness.FRESH]:
                    fresh += 1
                elif age < self.THRESHOLDS[DataFreshness.STALE]:
                    stale += 1
                elif age < self.THRESHOLDS[DataFreshness.CRITICAL]:
                    critical += 1
                else:
                    offline += 1
            else:
                offline += 1
        
        health_score = round((fresh + stale * 0.5) / total * 100, 1)
        
        return {
            "total": total,
            "fresh": fresh,
            "stale": stale,
            "critical": critical,
            "offline": offline,
            "health_score": health_score,
            "last_updated": last_updated.isoformat() if last_updated else None
        }
    
    async def get_stale_tenders(self, hours: int = 6) -> list[Tender]:
        """Get tenders that need refreshing."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        
        stmt = select(Tender).where(
            (Tender.scraped_at < cutoff) | (Tender.scraped_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
