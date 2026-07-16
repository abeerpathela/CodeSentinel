"""Deferred scan workspace lifecycle for Ship-to-GitHub."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from backend.config.settings import get_settings
from core.workspace_manager import WorkspaceManager
from core.github_handler import GitHubHandler


@dataclass
class WorkspaceRecord:
    scan_id: str
    created_at: float
    retain_until: float


_lock = threading.Lock()
_workspaces: dict[str, WorkspaceRecord] = {}


def register_workspace(scan_id: str) -> None:
    """Mark scan workspace as retained for deployment."""
    ttl = get_settings().scan_workspace_ttl_seconds
    now = time.time()
    with _lock:
        _workspaces[scan_id] = WorkspaceRecord(
            scan_id=scan_id,
            created_at=now,
            retain_until=now + ttl,
        )


def release_workspace(scan_id: str) -> None:
    """Remove workspace immediately (after successful deploy)."""
    with _lock:
        _workspaces.pop(scan_id, None)
    GitHubHandler.cleanup(WorkspaceManager.get_path(scan_id))


def sweep_expired_workspaces() -> list[str]:
    """Delete workspaces past TTL. Returns cleaned scan_ids."""
    now = time.time()
    expired: list[str] = []
    with _lock:
        for scan_id, rec in list(_workspaces.items()):
            if now >= rec.retain_until:
                expired.append(scan_id)
                _workspaces.pop(scan_id, None)
    for scan_id in expired:
        GitHubHandler.cleanup(WorkspaceManager.get_path(scan_id))
    return expired


def workspace_registered(scan_id: str) -> bool:
    with _lock:
        return scan_id in _workspaces
