from __future__ import annotations

import structlog
from celery import Celery

from app.config import settings

logger = structlog.get_logger()

# Create Celery app
celery_app = Celery(
    "tendercopilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.contexts.tender_discovery.tasks",
        "app.contexts.tender_intelligence.tasks",
        "app.contexts.bid_generation.tasks",
        "app.contexts.tender_matching.tasks",
        "app.contexts.bid_lifecycle.tasks",
        "app.contexts.bid_intelligence.tasks",
        "app.contexts.alert_engine.tasks",
        "app.contexts.whatsapp_gateway.tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
    beat_schedule={
        "check-expiring-documents": {
            "task": "compliance_vault.check_expiring_documents",
            "schedule": 3600.0,  # Every hour
        },
        "payment-follow-ups": {
            "task": "bid_lifecycle.payment_follow_ups",
            "schedule": 21600.0,  # Every 6 hours
        },
        "market-prices-refresh": {
            "task": "bid_intelligence.refresh_market_prices",
            "schedule": 86400.0,  # Daily at midnight
        },
    },
)

@celery_app.task(bind=True)
def debug_task(self):
    logger.info("celery_debug_task", request=self.request)
    return f"Request: {self.request!r}"
