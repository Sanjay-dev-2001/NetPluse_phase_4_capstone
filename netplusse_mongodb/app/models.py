import ipaddress
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DeviceCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "device_id": "router-01",
                    "name": "Core Router",
                    "device_type": "router",
                    "ip_address": "192.168.1.1",
                    "status": "online",
                }
            ]
        }
    )

    device_id: str
    name: str
    device_type: Literal["router", "switch", "server"]
    ip_address: ipaddress.IPv4Address
    status: Literal["online", "offline"] = "online"
    location: str | None = None


class DeviceResponse(BaseModel):
    device_id: str
    name: str
    device_type: Literal["router", "switch", "server"]
    ip_address: ipaddress.IPv4Address
    status: Literal["online", "offline"] = "online"
    location: str | None = None


class StatusUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "offline"}]})

    status: Literal["online", "offline"]


class AlertResponse(BaseModel):
    device_id: str
    message: str
    timestamp: datetime