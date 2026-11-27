from fastapi import APIRouter, Depends, HTTPException, status

from app.models import AlertResponse, DeviceCreate, DeviceResponse, StatusUpdate
from app.repositories.mongo_device_repository import MongoDeviceRepository
from app.services.device_service import (
    DeviceAlreadyExistsError,
    DeviceNotFoundError,
    DeviceService,
)

router = APIRouter()


def get_device_service() -> DeviceService:
    return DeviceService(MongoDeviceRepository())


@router.post(
    "/devices",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["devices"],
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "A device with this device_id already exists."
        }
    },
)
def register_device(
    device: DeviceCreate,
    device_service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    try:
        return device_service.register(device)
    except DeviceAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error


@router.get("/devices", response_model=list[DeviceResponse], tags=["devices"])
def list_devices(
    device_service: DeviceService = Depends(get_device_service),
) -> list[DeviceResponse]:
    return device_service.list()


@router.get(
    "/devices/{device_id}",
    response_model=DeviceResponse,
    tags=["devices"],
    responses={status.HTTP_404_NOT_FOUND: {"description": "Device not found."}},
)
def get_device(
    device_id: str,
    device_service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    try:
        return device_service.get(device_id)
    except DeviceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error


@router.patch(
    "/devices/{device_id}/status",
    response_model=DeviceResponse,
    tags=["devices"],
    responses={status.HTTP_404_NOT_FOUND: {"description": "Device not found."}},
)
def update_device_status(
    device_id: str,
    changes: StatusUpdate,
    device_service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    try:
        return device_service.update_status(device_id, changes)
    except DeviceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error


@router.get("/alerts", response_model=list[AlertResponse], tags=["alerts"])
def list_alerts(
    device_service: DeviceService = Depends(get_device_service),
) -> list[AlertResponse]:
    return device_service.list_alerts()


@router.get("/health", response_model=dict[str, str], tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}