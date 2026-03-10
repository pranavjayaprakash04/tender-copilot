from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

import structlog
from app.infrastructure.email_client import EmailClient
from celery import Celery
from celery.schedules import crontab

from app.contexts.alert_engine.schemas import AlertEvent
from app.contexts.alert_engine.service import AlertEngineService
from app.database import get_async_session
from app.infrastructure.whatsapp_client import WhatsAppClient

logger = structlog.get_logger()

celery_app = Celery('alert_engine_tasks')
celery_app.config_from_object('app.celery_config')


@celery_app.task(name="alert_engine.process_domain_events")
def process_domain_events_task() -> dict:
    """Process domain events from other contexts and send notifications."""
    async def _process_events():
        async with get_async_session() as session:
            # Initialize alert engine service
            from app.contexts.alert_engine.repository import (
                NotificationPreferenceRepository,
                NotificationRepository,
                NotificationTemplateRepository,
            )

            alert_service = AlertEngineService(
                notification_repo=NotificationRepository(session),
                template_repo=NotificationTemplateRepository(session),
                preference_repo=NotificationPreferenceRepository(session),
                email_client=EmailClient(),
                whatsapp_client=WhatsAppClient()
            )

            # Get unprocessed events
            # TODO: Implement actual event consumption from message queue
            # For now, simulate some events
            mock_events = [
                {
                    "event_type": "alerts_created",
                    "data": {
                        "alerts": [
                            {
                                "company_id": str(UUID("12345678-1234-5678-9abc-123456789abc")),
                                "alert_type": "deadline_reminder",
                                "tender_id": str(UUID("87654321-4321-8765-cba9-87654321cba9")),
                                "message": "Tender 'IT Infrastructure Upgrade' closing in 2 days!",
                                "urgency": "high"
                            }
                        ]
                    },
                    "trace_id": f"event-{datetime.utcnow().isoformat()}"
                }
            ]

            notifications_sent = 0

            for event_data in mock_events:
                if event_data["event_type"] == "alerts_created":
                    # Convert to AlertEvent objects
                    alert_events = [
                        AlertEvent(**alert_data) for alert_data in event_data["data"]["alerts"]
                    ]

                    # Send notifications
                    notifications = await alert_service.send_alerts_from_event(
                        alert_events, event_data["trace_id"]
                    )

                    notifications_sent += len(notifications)

                    # Mark event as processed
                    # TODO: Implement event marking in event store

                    logger.info(
                        "domain_event_processed",
                        event_type=event_data["event_type"],
                        alerts_count=len(alert_events),
                        notifications_sent=len(notifications),
                        trace_id=event_data["trace_id"]
                    )

            return {
                "status": "completed",
                "events_processed": len(mock_events),
                "notifications_sent": notifications_sent,
                "processed_at": datetime.utcnow().isoformat()
            }

    import asyncio
    return asyncio.run(_process_events())


@celery_app.task(name="alert_engine.retry_failed_notifications")
def retry_failed_notifications_task() -> dict:
    """Retry failed notifications that are ready for retry."""
    async def _retry_notifications():
        async with get_async_session() as session:
            # Initialize alert engine service
            from app.contexts.alert_engine.repository import (
                NotificationPreferenceRepository,
                NotificationRepository,
                NotificationTemplateRepository,
            )

            alert_service = AlertEngineService(
                notification_repo=NotificationRepository(session),
                template_repo=NotificationTemplateRepository(session),
                preference_repo=NotificationPreferenceRepository(session),
                email_client=EmailClient(),
                whatsapp_client=WhatsAppClient()
            )

            # Get all companies with failed notifications
            # TODO: Implement company listing
            company_ids = [UUID("12345678-1234-5678-9abc-123456789abc")]

            total_retried = 0

            for company_id in company_ids:
                retried = await alert_service.retry_failed_notifications(
                    company_id, f"retry-task-{datetime.utcnow().isoformat()}"
                )
                total_retried += len(retried)

            logger.info(
                "failed_notifications_retried",
                companies_processed=len(company_ids),
                total_retried=total_retried
            )

            return {
                "status": "completed",
                "companies_processed": len(company_ids),
                "total_retried": total_retried,
                "retried_at": datetime.utcnow().isoformat()
            }

    import asyncio
    return asyncio.run(_retry_notifications())


@celery_app.task(name="alert_engine.cleanup_old_notifications")
def cleanup_old_notifications_task() -> dict:
    """Clean up old notifications to maintain database performance."""
    async def _cleanup_notifications():
        async with get_async_session() as session:
            from app.contexts.alert_engine.repository import NotificationRepository

            notification_repo = NotificationRepository(session)

            # Delete notifications older than 90 days
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            deleted_count = await notification_repo.delete_old_notifications(cutoff_date)

            logger.info(
                "old_notifications_cleaned",
                cutoff_date=cutoff_date.isoformat(),
                deleted_count=deleted_count
            )

            return {
                "status": "completed",
                "cutoff_date": cutoff_date.isoformat(),
                "deleted_count": deleted_count,
                "cleaned_at": datetime.utcnow().isoformat()
            }

    import asyncio
    return asyncio.run(_cleanup_notifications())


@celery_app.task(name="alert_engine.send_daily_digest")
def send_daily_digest_task() -> dict:
    """Send daily digest of notifications to companies."""
    async def _send_digest():
        async with get_async_session() as session:
            from app.contexts.alert_engine.repository import (
                NotificationPreferenceRepository,
                NotificationRepository,
                NotificationTemplateRepository,
            )

            alert_service = AlertEngineService(
                notification_repo=NotificationRepository(session),
                template_repo=NotificationTemplateRepository(session),
                preference_repo=NotificationPreferenceRepository(session),
                email_client=EmailClient(),
                whatsapp_client=WhatsAppClient()
            )

            # Get companies that want daily digests
            # TODO: Implement digest preference checking
            company_ids = [UUID("12345678-1234-5678-9abc-123456789abc")]

            digests_sent = 0

            for company_id in company_ids:
                # Get notification stats for the day
                stats = await alert_service.get_notification_stats(
                    company_id, f"daily-digest-{datetime.utcnow().isoformat()}"
                )

                # Create digest notification
                from app.contexts.alert_engine.models import NotificationType
                from app.contexts.alert_engine.schemas import NotificationCreate

                digest_message = f"""
Daily Tender Alert Digest - {datetime.utcnow().strftime('%Y-%m-%d')}

📊 Summary:
- Total notifications: {stats.total_notifications}
- Sent successfully: {stats.sent_notifications}
- Failed: {stats.failed_notifications}
- Delivery rate: {stats.delivery_rate:.1%}%

📈 Notifications by type:
{chr(10).join([f"- {k}: {v}" for k, v in stats.notifications_by_type.items()])}

🔔 Priority breakdown:
{chr(10).join([f"- {k}: {v}" for k, v in stats.notifications_by_priority.items()])}
                """.strip()

                notification_data = NotificationCreate(
                    notification_type=NotificationType.EMAIL,
                    recipient=f"company-{company_id}@example.com",
                    subject="📊 Daily Tender Alert Digest",
                    message=digest_message,
                    priority="medium"
                )

                notification = await alert_service.create_notification(
                    notification_data, company_id, f"daily-digest-{datetime.utcnow().isoformat()}"
                )

                if notification:
                    digests_sent += 1

            logger.info(
                "daily_digests_sent",
                companies_processed=len(company_ids),
                digests_sent=digests_sent
            )

            return {
                "status": "completed",
                "companies_processed": len(company_ids),
                "digests_sent": digests_sent,
                "sent_at": datetime.utcnow().isoformat()
            }

    import asyncio
    return asyncio.run(_send_digest())


# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    'process-domain-events': {
        'task': 'alert_engine.process_domain_events',
        'schedule': 300.0,  # Every 5 minutes (Upstash free tier Redis constraint - can be more frequent after upgrade)
    },
    'retry-failed-notifications': {
        'task': 'alert_engine.retry_failed_notifications',
        'schedule': 900.0,  # Every 15 minutes (Upstash free tier Redis constraint - can be more frequent after upgrade)
    },
    'cleanup-old-notifications': {
        'task': 'alert_engine.cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'send-daily-digest': {
        'task': 'alert_engine.send_daily_digest',
        'schedule': crontab(hour=18, minute=0),  # 6 PM daily
    },
}

celery_app.conf.timezone = 'UTC'
