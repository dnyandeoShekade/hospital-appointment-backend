"""Services router."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceRead, ServiceUpdate
from app.services.service_service import create_service, delete_service, get_service, list_services, update_service

router = APIRouter(tags=["services"])


@router.get("/providers/{provider_id}/services", response_model=list[ServiceRead])
def list_services_endpoint(provider_id: uuid.UUID, db: Session = Depends(get_db)):
    return list_services(db, provider_id)


@router.post("/providers/{provider_id}/services", response_model=ServiceRead, status_code=201)
def create_service_endpoint(
    provider_id: uuid.UUID,
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_service(db, provider_id, current_user, payload)


@router.patch("/services/{service_id}", response_model=ServiceRead)
def update_service_endpoint(
    service_id: uuid.UUID,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_service(db, service_id, current_user, payload)


@router.delete("/services/{service_id}", status_code=204)
def delete_service_endpoint(
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_service(db, service_id, current_user)
    return None
