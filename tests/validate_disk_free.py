"""Validate scanner uses OS temp — never a hardcoded user/project path."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_ID = "disk_free_validation"


def main() -> None:
    from core.workspace import WorkspaceManager

    temp_root = Path(tempfile.gettempdir()).resolve()
    wm = WorkspaceManager.instance()
    ws = WorkspaceManager.get_workspace(TEST_ID)

    assert temp_root in ws.resolve().parents, "workspace must live under OS temp"
    assert ws.name.startswith("sentinel_"), "must use mkdtemp sentinel_ prefix"
    normalized = str(ws).replace("\\", "/").lower()
    assert "/backend/data" not in normalized, "must not use project data path"

    label = wm.temp_label(ws)
    print(f"[OK] Workspace label: {label}")
    print(f"[OK] OS temp root: {wm.describe_root()}")
    print(f"[OK] mkdtemp prefix verified: {ws.name.startswith('sentinel_')}")

    WorkspaceManager.release_workspace(TEST_ID)
    assert not ws.exists()
    print(f"[OK] Workspace released")

    print("\n=== validate_disk_free PASSED ===")


if __name__ == "__main__":
    main()
