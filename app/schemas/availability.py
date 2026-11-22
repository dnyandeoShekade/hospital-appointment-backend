"""Availability schemas."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import List

from pydantic import BaseModel


class WorkingHoursCreate(BaseModel):
    weekday: int
    start_time: time
    end_time: time


class WorkingHoursRead(WorkingHoursCreate):
    id: str


class BlockedTimeCreate(BaseModel):
    start_at: datetime
    end_at: datetime
    reason: str | None = None


class BlockedTimeRead(BlockedTimeCreate):
    id: str


class AvailabilitySlot(BaseModel):
    start_at: datetime
    end_at: datetime


class AvailabilityResponse(BaseModel):
    provider_id: str
    date: date
    service_id: str
    slots: List[AvailabilitySlot]
