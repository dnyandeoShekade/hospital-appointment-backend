"""SQLAlchemy models package. Importing this registers all models with Base metadata."""

from app.models.user import User, UserRole
from app.models.provider import ProviderProfile
from app.models.service import Service
from app.models.working_hours import WorkingHours
from app.models.blocked_time import BlockedTime
from app.models.appointment import Appointment, AppointmentStatus
from app.models.notification import Notification

__all__ = [
    "User",
    "UserRole",
    "ProviderProfile",
    "Service",
    "WorkingHours",
    "BlockedTime",
    "Appointment",
    "AppointmentStatus",
    "Notification",
]
