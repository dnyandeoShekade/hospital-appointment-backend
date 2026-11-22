"""Provider service logic."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import is_owner_or_admin
from app.models.provider import ProviderProfile
from app.models.service import Service
from app.models.user import User, UserRole
from app.models.working_hours import WorkingHours
from app.core.security import get_password_hash
from app.schemas.provider import AdminProviderCreate


def list_providers(db: Session, search: str | None = None, skip: int = 0, limit: int = 20) -> list[ProviderProfile]:
    stmt = select(ProviderProfile).options(selectinload(ProviderProfile.user))
    if search:
        stmt = stmt.where(ProviderProfile.specialty.ilike(f"%{search}%"))
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def create_provider_for_admin(db: Session, payload: AdminProviderCreate) -> ProviderProfile:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=UserRole.PROVIDER,
    )
    provider = ProviderProfile(
        user=user,
        specialty=payload.specialty,
        bio=payload.bio,
        timezone=payload.timezone,
        is_approved=True,
    )
    db.add(provider)
    db.flush()

    service_data = payload.service.model_dump()
    db.add(Service(provider_id=provider.id, **service_data))
    db.add_all(
        WorkingHours(provider_id=provider.id, **hours.model_dump())
        for hours in payload.working_hours
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(provider)
    return provider


def get_provider(db: Session, provider_id: uuid.UUID) -> ProviderProfile:
    provider = db.get(ProviderProfile, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return provider


def create_provider_profile(db: Session, current_user: User, payload) -> ProviderProfile:
    if current_user.role not in (UserRole.PROVIDER, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only providers can create profiles")
    existing = db.scalar(select(ProviderProfile).where(ProviderProfile.user_id == current_user.id))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists")
    provider = ProviderProfile(user_id=current_user.id, **payload.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def update_provider_profile(db: Session, provider_id: uuid.UUID, current_user: User, payload) -> ProviderProfile:
    provider = get_provider(db, provider_id)
    if not is_owner_or_admin(provider.user_id, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    data = payload.model_dump(exclude_unset=True)
    # only admins can change approval
    if "is_approved" in data and current_user.role != UserRole.ADMIN:
        data.pop("is_approved", None)
    for key, value in data.items():
        setattr(provider, key, value)
    db.commit()
    db.refresh(provider)
    return provider
