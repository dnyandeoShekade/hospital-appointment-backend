"""Provider router."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.provider import ProviderProfileCreate, ProviderProfileRead, ProviderProfileUpdate
from app.services.provider_service import create_provider_profile, get_provider, list_providers, update_provider_profile

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderProfileRead])
def list_providers_endpoint(
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
) -> list:
    return list_providers(db, search=search, skip=skip, limit=limit)


@router.get("/{provider_id}", response_model=ProviderProfileRead)
def get_provider_endpoint(provider_id: uuid.UUID, db: Session = Depends(get_db)):
    return get_provider(db, provider_id)


@router.post("", response_model=ProviderProfileRead, status_code=201)
def create_provider_endpoint(
    payload: ProviderProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_provider_profile(db, current_user, payload)


@router.patch("/{provider_id}", response_model=ProviderProfileRead)
def update_provider_endpoint(
    provider_id: uuid.UUID,
    payload: ProviderProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_provider_profile(db, provider_id, current_user, payload)
