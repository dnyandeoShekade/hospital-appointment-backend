"""Availability and working-hours logic."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import is_owner_or_admin
from app.models.appointment import Appointment
from app.models.blocked_time import BlockedTime
from app.models.provider import ProviderProfile
from app.models.service import Service
from app.models.user import User
from app.models.working_hours import WorkingHours
from app.schemas.availability import BlockedTimeCreate, WorkingHoursCreate


def _provider_owned(db: Session, provider_id: uuid.UUID, current_user: User) -> ProviderProfile:
    provider = db.get(ProviderProfile, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    if not is_owner_or_admin(provider.user_id, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return provider


def add_working_hours(db: Session, provider_id: uuid.UUID, current_user: User, payload: WorkingHoursCreate) -> WorkingHours:
    _provider_owned(db, provider_id, current_user)
    if not (0 <= payload.weekday <= 6):
        raise HTTPException(status_code=422, detail="weekday must be 0-6")
    if payload.start_time >= payload.end_time:
        raise HTTPException(status_code=422, detail="start_time must be before end_time")
    # overlap check
    existing = db.scalars(
        select(WorkingHours).where(WorkingHours.provider_id == provider_id, WorkingHours.weekday == payload.weekday)
    ).all()
    for wh in existing:
        if not (payload.end_time <= wh.start_time or payload.start_time >= wh.end_time):
            raise HTTPException(status_code=409, detail="Overlapping working period")
    wh = WorkingHours(provider_id=provider_id, weekday=payload.weekday, start_time=payload.start_time, end_time=payload.end_time)
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


def add_blocked_time(db: Session, provider_id: uuid.UUID, current_user: User, payload: BlockedTimeCreate) -> BlockedTime:
    _provider_owned(db, provider_id, current_user)
    if payload.start_at >= payload.end_at:
        raise HTTPException(status_code=422, detail="start_at must be before end_at")
    bt = BlockedTime(provider_id=provider_id, start_at=payload.start_at, end_at=payload.end_at, reason=payload.reason)
    db.add(bt)
    db.commit()
    db.refresh(bt)
    return bt


def get_availability(db: Session, provider_id: uuid.UUID, target_date: date, service_id: uuid.UUID) -> list[dict]:
    provider = db.get(ProviderProfile, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    service = db.get(Service, service_id)
    if service is None or service.provider_id != provider_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    duration = timedelta(minutes=service.duration_minutes)
    tz = ZoneInfo(provider.timezone)
    # working hours for weekday
    weekday = target_date.weekday()
    # Python Monday=0; keep as is (0-6)
    periods = db.scalars(
        select(WorkingHours).where(WorkingHours.provider_id == provider_id, WorkingHours.weekday == weekday)
    ).all()
    # blocked times overlapping date
    day_start = datetime.combine(target_date, time.min, tzinfo=tz).astimezone(timezone.utc)
    day_end = datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc)
    blocked = db.scalars(
        select(BlockedTime).where(
            BlockedTime.provider_id == provider_id,
            BlockedTime.start_at < day_end,
            BlockedTime.end_at > day_start,
        )
    ).all()
    # existing active appointments
    appts = db.scalars(
        select(Appointment).where(
            Appointment.provider_id == provider_id,
            Appointment.start_at < day_end,
            Appointment.end_at > day_start,
            Appointment.status != "cancelled",
        )
    ).all()

    now = datetime.now(timezone.utc)
    slots = []
    for wh in periods:
        # build datetime for start/end of period on target_date
        period_start = datetime.combine(target_date, wh.start_time, tzinfo=tz).astimezone(timezone.utc)
        period_end = datetime.combine(target_date, wh.end_time, tzinfo=tz).astimezone(timezone.utc)
        cursor = period_start
        while cursor + duration <= period_end:
            slot_end = cursor + duration
            # exclude past
            if cursor >= now:
                # check blocked
                blocked_hit = any(b.start_at < slot_end and b.end_at > cursor for b in blocked)
                # check appointments
                appt_hit = any(a.start_at < slot_end and a.end_at > cursor for a in appts)
                if not blocked_hit and not appt_hit:
                    slots.append({"start_at": cursor, "end_at": slot_end})
            cursor += timedelta(minutes=15)  # slot step 15 min; could be duration
    return slots
