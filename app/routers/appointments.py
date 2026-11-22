"""Appointments router."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.appointment import AppointmentCreate, AppointmentRead, CancelRequest, RescheduleRequest
from app.services.appointment_service import (
    cancel_appointment,
    create_appointment,
    get_appointment,
    list_my_appointments,
    reschedule_appointment,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentRead, status_code=201)
def create_endpoint(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_appointment(
        db,
        current_user,
        payload.provider_id,
        payload.service_id,
        payload.start_at,
        payload.customer_notes,
    )


@router.get("/me", response_model=list[AppointmentRead])
def me_endpoint(
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_my_appointments(db, current_user, status_filter=status, skip=skip, limit=limit)


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_endpoint(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_appointment(db, appointment_id, current_user)


@router.patch("/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_endpoint(
    appointment_id: uuid.UUID,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return cancel_appointment(db, appointment_id, current_user, payload.reason)


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentRead)
def reschedule_endpoint(
    appointment_id: uuid.UUID,
    payload: RescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return reschedule_appointment(db, appointment_id, current_user, payload.start_at)
