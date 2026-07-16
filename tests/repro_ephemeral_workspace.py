"""Verify ephemeral workspace — no hardcoded user disk paths."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_ID = "ephemeral_scan_test"


def main() -> None:
    from backend.config import get_settings
    from backend.services.github_deploy import GitHubDeployService
    from core.github_deploy import prepare_fresh_repository
    from core.workspace import WorkspaceManager

    settings = get_settings()
    wm = WorkspaceManager.instance()
    temp_base = Path(tempfile.gettempdir()).resolve()
    assert temp_base == wm.root.resolve()

    print(f"[OK] Ephemeral workspace root: {wm.describe_root()}")

    dest = WorkspaceManager.get_workspace(TEST_ID)
    assert dest.name.startswith("sentinel_")
    (dest / "main.py").write_text("print('ephemeral audit')\n", encoding="utf-8")
    (dest / ".git").mkdir()
    (dest / ".git" / "shallow").write_text("mock\n", encoding="utf-8")

    svc = GitHubDeployService()
    resolved = svc.resolve_deploy_path(TEST_ID)
    assert resolved == dest
    print("[OK] Deploy resolver located workspace by scan_id only")

    prepare_fresh_repository(dest)
    assert not (dest / ".git" / "shallow").exists()
    print("[OK] Fresh-source prep scrubbed shallow clone metadata")

    WorkspaceManager.release_workspace(TEST_ID)
    assert not dest.exists()
    print(f"[OK] Workspace {TEST_ID} cleaned up")

    print(f"[INFO] storage_type={settings.workspace_storage_type}")
    print("\n=== repro_ephemeral_workspace PASSED ===")


if __name__ == "__main__":
    main()
