"""Availability router."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.availability import AvailabilitySlot, BlockedTimeCreate, WorkingHoursCreate
from app.services.availability_service import add_blocked_time, add_working_hours, get_availability

router = APIRouter(tags=["availability"])


@router.get("/providers/{provider_id}/availability")
def availability_endpoint(
    provider_id: uuid.UUID,
    date: date = Query(...),
    service_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
):
    slots = get_availability(db, provider_id, date, service_id)
    return {
        "provider_id": str(provider_id),
        "date": date,
        "service_id": str(service_id),
        "slots": [AvailabilitySlot(start_at=s["start_at"], end_at=s["end_at"]) for s in slots],
    }


@router.post("/providers/{provider_id}/working-hours", status_code=201)
def create_working_hours_endpoint(
    provider_id: uuid.UUID,
    payload: WorkingHoursCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wh = add_working_hours(db, provider_id, current_user, payload)
    return {"id": str(wh.id), "weekday": wh.weekday, "start_time": wh.start_time, "end_time": wh.end_time}


@router.post("/providers/{provider_id}/blocked-times", status_code=201)
def create_blocked_time_endpoint(
    provider_id: uuid.UUID,
    payload: BlockedTimeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bt = add_blocked_time(db, provider_id, current_user, payload)
    return {"id": str(bt.id), "start_at": bt.start_at, "end_at": bt.end_at, "reason": bt.reason}
