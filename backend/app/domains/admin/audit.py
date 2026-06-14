"""Audit logging helper — call this from services on any sensitive access.

Append-only. Used for PDPA/GDPR accountability and the Consent access log.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.admin.models import AuditLog


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    resource_type: str,
    actor_id: str | uuid.UUID | None = None,
    org_id: str | uuid.UUID | None = None,
    resource_id: str | None = None,
    ip: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=uuid.UUID(str(actor_id)) if actor_id else None,
            org_id=uuid.UUID(str(org_id)) if org_id else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip=ip,
            detail=detail or {},
        )
    )
