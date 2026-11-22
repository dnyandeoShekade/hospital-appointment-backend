"""Service management logic."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import is_owner_or_admin
from app.models.provider import ProviderProfile
from app.models.service import Service
from app.models.user import User


def list_services(db: Session, provider_id: uuid.UUID) -> list[Service]:
    return list(db.scalars(select(Service).where(Service.provider_id == provider_id)).all())


def get_service(db: Session, service_id: uuid.UUID) -> Service:
    service = db.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


def _provider_for_user(db: Session, provider_id: uuid.UUID, current_user: User) -> ProviderProfile:
    provider = db.get(ProviderProfile, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    if not is_owner_or_admin(provider.user_id, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return provider


def create_service(db: Session, provider_id: uuid.UUID, current_user: User, payload) -> Service:
    _provider_for_user(db, provider_id, current_user)
    service = Service(provider_id=provider_id, **payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def update_service(db: Session, service_id: uuid.UUID, current_user: User, payload) -> Service:
    service = get_service(db, service_id)
    provider = db.get(ProviderProfile, service.provider_id)
    if provider is None or not is_owner_or_admin(provider.user_id, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


def delete_service(db: Session, service_id: uuid.UUID, current_user: User) -> None:
    service = get_service(db, service_id)
    provider = db.get(ProviderProfile, service.provider_id)
    if provider is None or not is_owner_or_admin(provider.user_id, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    service.is_active = False
    db.commit()
