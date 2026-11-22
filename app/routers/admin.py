"""Administrator-only setup routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.provider import AdminProviderCreate, ProviderProfileRead
from app.services.provider_service import create_provider_for_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/providers", response_model=ProviderProfileRead, status_code=201)
def create_provider_endpoint(
    payload: AdminProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> object:
    return create_provider_for_admin(db, payload)
