import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.models import AlertResponse
from app.repositories.device_repository import InMemoryDeviceRepository

logger = logging.getLogger(__name__)


class DomainEvent(BaseModel):
    event_type: str
    aggregate_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)


def publish_event(event: DomainEvent) -> None:
    logger.info("domain_event=%s", event.model_dump_json())


def create_offline_alert(
    repository: InMemoryDeviceRepository, device_id: str
) -> None:
    alert = AlertResponse(
        device_id=device_id,
        message=f"Device {device_id} went offline.",
        timestamp=datetime.now(timezone.utc),
    )
    repository.save_alert(alert)