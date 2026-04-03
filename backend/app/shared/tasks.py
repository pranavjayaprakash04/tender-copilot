from __future__ import annotations

from typing import Any


class BaseTask:
    """Base task class for Celery tasks."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        pass
    
    def task(self, *args, **kwargs):
        """Create a task decorator."""
        def decorator(func):
            return func
        return decorator


class MockTask:
    """Mock task for testing."""
    
    def __init__(self, task_id: str):
        self.id = task_id
    
    def delay(self, *args, **kwargs):
        """Mock delay method."""
        return self


# Mock Celery tasks for WhatsApp
def send_whatsapp_alert(*args, **kwargs) -> MockTask:
    """Mock WhatsApp alert task."""
    return MockTask("mock-whatsapp-task")


def send_bulk_whatsapp_alerts(*args, **kwargs) -> MockTask:
    """Mock bulk WhatsApp alert task."""
    return MockTask("mock-bulk-whatsapp-task")
