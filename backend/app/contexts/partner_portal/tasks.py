from __future__ import annotations

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task
def bulk_bid_generation_task(ca_id: str, company_ids: list[str], tender_id: str) -> None:
    """Bulk bid generation task for CA partners."""
    try:
        logger.info(
            "bulk_bid_generation_started",
            ca_id=ca_id,
            company_count=len(company_ids),
            tender_id=tender_id,
        )

        for company_id in company_ids:
            try:
                # TODO: Dispatch individual bid generation task
                # bid_generation_task.delay(company_id, tender_id)
                logger.info(
                    "bid_generation_dispatched",
                    ca_id=ca_id,
                    company_id=company_id,
                    tender_id=tender_id,
                )
            except Exception as e:
                logger.error(
                    "bid_generation_dispatch_error",
                    ca_id=ca_id,
                    company_id=company_id,
                    tender_id=tender_id,
                    error=str(e),
                )

        logger.info(
            "bulk_bid_generation_completed",
            ca_id=ca_id,
            company_count=len(company_ids),
            tender_id=tender_id,
        )
    except Exception as e:
        logger.error(
            "bulk_bid_generation_task_error",
            ca_id=ca_id,
            tender_id=tender_id,
            error=str(e),
        )


@shared_task
def bulk_alert_dispatch_task(ca_id: str, company_ids: list[str], message: str, alert_type: str) -> None:
    """Bulk alert dispatch task for CA partners."""
    try:
        logger.info(
            "bulk_alert_dispatch_started",
            ca_id=ca_id,
            company_count=len(company_ids),
            alert_type=alert_type,
        )

        for company_id in company_ids:
            try:
                # TODO: Log alert in alert_engine
                logger.info(
                    "alert_logged",
                    ca_id=ca_id,
                    company_id=company_id,
                    message=message,
                    alert_type=alert_type,
                )
            except Exception as e:
                logger.error(
                    "alert_log_error",
                    ca_id=ca_id,
                    company_id=company_id,
                    message=message,
                    alert_type=alert_type,
                    error=str(e),
                )

        logger.info(
            "bulk_alert_dispatch_completed",
            ca_id=ca_id,
            company_count=len(company_ids),
            alert_type=alert_type,
        )
    except Exception as e:
        logger.error(
            "bulk_alert_dispatch_task_error",
            ca_id=ca_id,
            alert_type=alert_type,
            error=str(e),
        )
