"""Appointment booking logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import is_owner_or_admin
from app.models.appointment import Appointment, AppointmentStatus
from app.models.blocked_time import BlockedTime
from app.models.provider import ProviderProfile
from app.models.service import Service
from app.models.user import User, UserRole
from app.models.working_hours import WorkingHours


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _validate_slot(
    db: Session,
    provider: ProviderProfile,
    service: Service,
    start_at: datetime,
    exclude_appointment_id: uuid.UUID | None = None,
) -> datetime:
    start_at = _ensure_utc(start_at)
    now = datetime.now(timezone.utc)
    if start_at < now:
        raise HTTPException(status_code=400, detail="Cannot book in the past")
    end_at = start_at + timedelta(minutes=service.duration_minutes)
    tz = ZoneInfo(provider.timezone)
    local_start = start_at.astimezone(tz)
    weekday = local_start.weekday()
    periods = db.scalars(
        select(WorkingHours).where(WorkingHours.provider_id == provider.id, WorkingHours.weekday == weekday)
    ).all()
    fits = False
    for p in periods:
        period_start = datetime.combine(local_start.date(), p.start_time, tzinfo=tz)
        period_end = datetime.combine(local_start.date(), p.end_time, tzinfo=tz)
        if period_start <= local_start and local_start + timedelta(minutes=service.duration_minutes) <= period_end:
            fits = True
            break
    if not fits:
        raise HTTPException(status_code=400, detail="Outside working hours")

    blocked = db.scalars(
        select(BlockedTime).where(
            BlockedTime.provider_id == provider.id,
            BlockedTime.start_at < end_at,
            BlockedTime.end_at > start_at,
        )
    ).all()
    if blocked:
        raise HTTPException(status_code=409, detail="Slot is blocked")

    stmt = select(Appointment).where(
        Appointment.provider_id == provider.id,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.start_at < end_at,
        Appointment.end_at > start_at,
    )
    if exclude_appointment_id is not None:
        stmt = stmt.where(Appointment.id != exclude_appointment_id)
    conflicts = db.scalars(stmt).all()
    if conflicts:
        raise HTTPException(status_code=409, detail="Slot conflicts with existing appointment")
    return end_at


def create_appointment(db: Session, current_user: User, provider_id: uuid.UUID, service_id: uuid.UUID, start_at: datetime, customer_notes: str | None = None) -> Appointment:
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Only customers can book")
    provider = db.get(ProviderProfile, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    service = db.get(Service, service_id)
    if service is None or service.provider_id != provider_id or not service.is_active:
        raise HTTPException(status_code=404, detail="Service not found")
    db.execute(select(ProviderProfile).where(ProviderProfile.id == provider_id).with_for_update())
    start_at = _ensure_utc(start_at)
    end_at = _validate_slot(db, provider, service, start_at)
    appt = Appointment(
        customer_id=current_user.id,
        provider_id=provider_id,
        service_id=service_id,
        start_at=start_at,
        end_at=end_at,
        status=AppointmentStatus.PENDING,
        customer_notes=customer_notes,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


def get_appointment(db: Session, appointment_id: uuid.UUID, current_user: User) -> Appointment:
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    provider = db.get(ProviderProfile, appt.provider_id)
    allowed = (
        current_user.role == UserRole.ADMIN
        or appt.customer_id == current_user.id
        or (provider is not None and provider.user_id == current_user.id)
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Not allowed")
    return appt


def list_my_appointments(db: Session, current_user: User, status_filter: str | None = None, skip: int = 0, limit: int = 20) -> list[Appointment]:
    stmt = select(Appointment)
    if current_user.role == UserRole.CUSTOMER:
        stmt = stmt.where(Appointment.customer_id == current_user.id)
    elif current_user.role == UserRole.PROVIDER:
        profile = db.scalar(select(ProviderProfile).where(ProviderProfile.user_id == current_user.id))
        if profile is None:
            return []
        stmt = stmt.where(Appointment.provider_id == profile.id)
    if status_filter:
        stmt = stmt.where(Appointment.status == status_filter)
    stmt = stmt.offset(skip).limit(limit).order_by(Appointment.start_at.desc())
    return list(db.scalars(stmt).all())


def cancel_appointment(db: Session, appointment_id: uuid.UUID, current_user: User, reason: str | None = None) -> Appointment:
    appt = get_appointment(db, appointment_id, current_user)
    if appt.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
        raise HTTPException(status_code=400, detail="Cannot cancel this appointment")
    provider = db.get(ProviderProfile, appt.provider_id)
    is_provider_owner = provider is not None and provider.user_id == current_user.id
    if not (current_user.role == UserRole.ADMIN or appt.customer_id == current_user.id or is_provider_owner):
        raise HTTPException(status_code=403, detail="Not allowed")
    appt.status = AppointmentStatus.CANCELLED
    appt.cancellation_reason = reason
    db.commit()
    db.refresh(appt)
    return appt


def reschedule_appointment(db: Session, appointment_id: uuid.UUID, current_user: User, new_start: datetime) -> Appointment:
    appt = get_appointment(db, appointment_id, current_user)
    if appt.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
        raise HTTPException(status_code=400, detail="Cannot reschedule this appointment")
    provider = db.get(ProviderProfile, appt.provider_id)
    service = db.get(Service, appt.service_id)
    if provider is None or service is None:
        raise HTTPException(status_code=404, detail="Provider or service not found")
    db.execute(select(ProviderProfile).where(ProviderProfile.id == provider.id).with_for_update())
    new_start = _ensure_utc(new_start)
    new_end = _validate_slot(db, provider, service, new_start, exclude_appointment_id=appt.id)
    appt.start_at = new_start
    appt.end_at = new_end
    appt.status = AppointmentStatus.PENDING
    db.commit()
    db.refresh(appt)
    return appt
