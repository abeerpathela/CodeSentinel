"""Backward-compatible path helpers — delegates to WorkspaceManager."""

from __future__ import annotations

from pathlib import Path

from backend.config.settings import PROJECT_ROOT, get_settings
from core.workspace_manager import WorkspaceManager


def ensure_temp_scan_root() -> Path:
    return WorkspaceManager.instance().ensure_root()


def resolve_scan_path(scan_id: str) -> Path:
    return WorkspaceManager.get_path(scan_id)


SCAN_WORKSPACE_TTL_SECONDS = get_settings().scan_workspace_ttl_seconds
TEMP_SCAN_ROOT = WorkspaceManager.instance().root

__all__ = [
    "PROJECT_ROOT",
    "SCAN_WORKSPACE_TTL_SECONDS",
    "TEMP_SCAN_ROOT",
    "ensure_temp_scan_root",
    "resolve_scan_path",
]
