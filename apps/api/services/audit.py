"""Audit trail service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.api.db.models import AuditLog


def log_action(
    db: Session,
    action: str,
    study_id: str | None = None,
    actor: str = "system",
    detail: dict | None = None,
) -> AuditLog:
    entry = AuditLog(study_id=study_id, actor=actor, action=action, detail=detail or {})
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
