"""Central path configuration for CodeSentinel backend."""

from __future__ import annotations

import os
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _CONFIG_DIR.parent
PROJECT_ROOT = _BACKEND_ROOT.parent

# backend/data/temp_scans — unified workspace root for cloned/staged scans
TEMP_SCAN_ROOT = _BACKEND_ROOT / "data" / "temp_scans"

# Retain workspaces for Ship-to-GitHub (seconds)
SCAN_WORKSPACE_TTL_SECONDS = int(os.getenv("SCAN_WORKSPACE_TTL_SECONDS", "3600"))


def ensure_temp_scan_root() -> Path:
    TEMP_SCAN_ROOT.mkdir(parents=True, exist_ok=True)
    return TEMP_SCAN_ROOT


def resolve_scan_path(scan_id: str) -> Path:
    """Reconstruct scan workspace path from scan_id at runtime."""
    return TEMP_SCAN_ROOT / scan_id
