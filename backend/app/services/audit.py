"""Audit logging service — records admin actions."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    action: str,
    *,
    user_id: int | None = None,
    details: str = "",
    ip_address: str = "",
) -> None:
    """Record an admin action in the audit log."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
