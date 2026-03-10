from __future__ import annotations

from datetime import datetime

import structlog
from celery import Celery
from celery.schedules import crontab

from app.contexts.tender_discovery.repository import (
    TenderAlertRepository,
    TenderRepository,
)
from app.contexts.tender_discovery.schemas import TenderAlertCreate
from app.database import get_async_session
from app.shared.events import DomainEventPublisher

logger = structlog.get_logger()

celery_app = Celery('tender_discovery_tasks')
celery_app.config_from_object('app.celery_config')


@celery_app.task(
    bind=True,
    name="tender_discovery.scrape_gem_portal",
    max_retries=3,
    default_retry_delay=300  # 5 minutes retry for government portal timeouts
)
def scrape_gem_portal_task(self) -> dict:
    """Scrape tenders from GeM (Government e-Marketplace) portal."""
    async def _scrape():
        async with get_async_session() as session:
            event_publisher = DomainEventPublisher()

            # Placeholder for GeM scraping logic
            scraped_tenders = []

            # TODO: Implement actual GeM portal scraping
            # - Login to GeM portal
            # - Navigate to tender sections
            # - Extract tender data
            # - Parse and standardize

            logger.info("gem_scraping_completed", tenders_found=len(scraped_tenders))

            # Publish domain event for new tenders
            if scraped_tenders:
                await event_publisher.publish(
                    event_type="tenders_discovered",
                    data={"source": "gem", "count": len(scraped_tenders)},
                    trace_id=f"gem-scrape-{datetime.utcnow().isoformat()}"
                )

            return {
                "status": "completed",
                "source": "gem",
                "tenders_found": len(scraped_tenders),
                "scraped_at": datetime.utcnow().isoformat()
            }

    import asyncio
    return asyncio.run(_scrape())


@celery_app.task(
    bind=True,
    name="tender_discovery.scrape_cppp_portal",
    max_retries=3,
    default_retry_delay=300  # 5 minutes retry for government portal timeouts
)
def scrape_cppp_portal_task(self) -> dict:
    """Scrape tenders from CPPP (Central Public Procurement Portal)."""
    async def _scrape():
        async with get_async_session() as session:
            event_publisher = DomainEventPublisher()

            # Placeholder for CPPP scraping logic
            scraped_tenders = []

            # TODO: Implement actual CPPP scraping using Playwright
            # Required selectors structure:
            # - Login: page.locator('input[id="username"]').fill(username)
            # - Password: page.locator('input[id="password"]').fill(password)
            # - Captcha: page.locator('input[id="captcha"]').fill(captcha_text)
            # - Search: page.locator('input[placeholder="Search Tenders"]').fill(keywords)
            # - Results: page.locator('table.tender-table tbody tr')
            # - Tender link: result.locator('a.tender-link').get_attribute('href')
            # - Extract fields:
            #   - Title: page.locator('h1.tender-title').text_content()
            #   - Reference: page.locator('span.ref-number').text_content()
            #   - Deadline: page.locator('span.deadline').text_content()
            #   - Value: page.locator('span.estimated-value').text_content()
            #   - Organization: page.locator('span.org-name').text_content()
            #   - Category: page.locator('span.category').text_content()
            #   - Documents: page.locator('a.document-link').get_attribute('href')

            logger.info("cppp_scraping_completed", tenders_found=len(scraped_tenders))

            # Publish domain event for new tenders
            if scraped_tenders:
                await event_publisher.publish(
                    event_type="tenders_discovered",
                    data={"source": "cppp", "count": len(scraped_tenders)},
                    trace_id=f"cppp-scrape-{datetime.utcnow().isoformat()}"
                )

            return {
                "status": "completed",
                "source": "cppp",
                "tenders_found": len(scraped_tenders),
                "scraped_at": datetime.utcnow().isoformat()
            }

    import asyncio
    return asyncio.run(_scrape())


@celery_app.task(name="tender_discovery.process_deadline_alerts")
def process_deadline_alerts_task() -> dict:
    """Process and create deadline alerts for approaching tenders."""
    async def _process_alerts():
        async with get_async_session() as session:
            tender_repo = TenderRepository(session)
            alert_repo = TenderAlertRepository(session)
            event_publisher = DomainEventPublisher()

            # Get tenders closing in 3 days
            urgent_tenders = await tender_repo.get_closing_soon(days=3)

            alerts_created = 0
            alert_events = []

            for tender in urgent_tenders:
                # Check if alert already exists
                existing_alerts = await alert_repo.get_by_company(tender.company_id)
                alert_exists = any(
                    alert.tender_id == tender.id and alert.alert_type == "deadline_reminder"
                    for alert in existing_alerts
                )

                if not alert_exists:
                    alert_data = TenderAlertCreate(
                        company_id=tender.company_id,
                        tender_id=tender.id,
                        alert_type="deadline_reminder",
                        message=f"Tender '{tender.title}' closing in {tender.days_until_deadline} days!"
                    )

                    await alert_repo.create(alert_data)
                    alerts_created += 1

                    # Create alert event for notification engine
                    alert_events.append({
                        "company_id": str(tender.company_id),
                        "alert_type": "deadline_reminder",
                        "tender_id": str(tender.id),
                        "message": alert_data.message,
                        "urgency": "high" if tender.days_until_deadline <= 1 else "medium"
                    })

            # Publish alert events for notification engine
            if alert_events:
                await event_publisher.publish(
                    event_type="alerts_created",
                    data={"alerts": alert_events},
                    trace_id=f"deadline-alerts-{datetime.utcnow().isoformat()}"
                )

            logger.info("deadline_alerts_processed", alerts_created=alerts_created)

            return {
                "status": "completed",
                "alerts_created": alerts_created,
                "urgent_tenders": len(urgent_tenders)
            }

    import asyncio
    return asyncio.run(_process_alerts())


# Schedule periodic scraping
celery_app.conf.beat_schedule = {
    'gem-scraping': {
        'task': 'tender_discovery.scrape_gem_portal',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'cppp-scraping': {
        'task': 'tender_discovery.scrape_cppp_portal',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
    'deadline-alerts': {
        'task': 'tender_discovery.process_deadline_alerts',
        'schedule': crontab(hour=9, minute=0),  # 9 AM daily
    },
}

celery_app.conf.timezone = 'UTC'
