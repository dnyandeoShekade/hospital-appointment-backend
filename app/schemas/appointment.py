"""Appointment schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AppointmentCreate(BaseModel):
    provider_id: uuid.UUID
    service_id: uuid.UUID
    start_at: datetime
    customer_notes: str | None = None


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    provider_id: uuid.UUID
    service_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    status: str
    customer_notes: str | None = None
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class CancelRequest(BaseModel):
    reason: str | None = None


class RescheduleRequest(BaseModel):
    start_at: datetime
