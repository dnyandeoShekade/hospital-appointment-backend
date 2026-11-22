"""Provider schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.availability import WorkingHoursCreate
from app.schemas.service import ServiceCreate


class ProviderProfileBase(BaseModel):
    specialty: str | None = None
    bio: str | None = None
    timezone: str = "UTC"


class ProviderProfileCreate(ProviderProfileBase):
    pass


class ProviderProfileUpdate(BaseModel):
    specialty: str | None = None
    bio: str | None = None
    timezone: str | None = None
    is_approved: bool | None = None


class ProviderProfileRead(ProviderProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    is_approved: bool
    created_at: datetime
    updated_at: datetime


class AdminProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    specialty: str = Field(min_length=1, max_length=255)
    bio: str | None = None
    timezone: str = "Asia/Kolkata"
    service: ServiceCreate
    working_hours: list[WorkingHoursCreate] = Field(min_length=1)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Use a valid IANA time zone, such as Asia/Kolkata") from exc
        return value

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be no more than 72 UTF-8 bytes")
        return value

    @model_validator(mode="after")
    def validate_working_hours(self) -> "AdminProviderCreate":
        weekdays = set()
        for hours in self.working_hours:
            if not 0 <= hours.weekday <= 6:
                raise ValueError("Working hour weekday must be between 0 (Monday) and 6 (Sunday)")
            if hours.start_time >= hours.end_time:
                raise ValueError("Working hour end time must be later than start time")
            if hours.weekday in weekdays:
                raise ValueError("Add at most one working period per weekday")
            weekdays.add(hours.weekday)
        return self
