"""Regression test — Ship-to-GitHub resolves workspace by scan_id only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_ID = "test_id_123"


def main() -> None:
    from backend.config.path_config import resolve_scan_path
    from backend.services.github_deploy import GitHubDeployService, ScanWorkspaceGoneError
    from backend.services.scan_session import register_workspace
    from core.github_handler import GitHubHandler

    handler = GitHubHandler()
    dest = resolve_scan_path(TEST_ID)
    if dest.exists():
        handler.cleanup(dest)
    dest.mkdir(parents=True)
    (dest / "README.md").write_text("# mock clone for ship test\n", encoding="utf-8")

    rel = dest.relative_to(ROOT)
    print(f"[OK] Mock workspace created at {rel.as_posix()}")
    assert dest.is_dir(), "workspace missing"
    register_workspace(TEST_ID)

    svc = GitHubDeployService()
    resolved = svc.resolve_deploy_path(TEST_ID)
    rel_resolved = resolved.relative_to(ROOT)
    print(f"[OK] resolve_deploy_path -> {rel_resolved.as_posix()}")

    assert resolved == dest, "path mismatch between resolve_scan_path and deploy resolver"

    try:
        svc.push_to_private_repo("fake-token", "codesentinel-test", TEST_ID)
        print("[FAIL] Expected push to fail with fake token", file=sys.stderr)
        sys.exit(1)
    except ScanWorkspaceGoneError:
        print("[FAIL] Workspace incorrectly reported gone", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"[OK] Deploy located workspace; git/api rejected as expected ({type(exc).__name__})")

    handler.cleanup(dest)
    assert not dest.exists(), "cleanup failed"
    print(f"[OK] Workspace {TEST_ID} cleaned up after test")

    try:
        svc.resolve_deploy_path(TEST_ID)
        print("[FAIL] Expected 410-style error for missing workspace", file=sys.stderr)
        sys.exit(1)
    except ScanWorkspaceGoneError as exc:
        assert TEST_ID in str(exc)
        print(f"[OK] Missing workspace error: {exc}")

    print("\n=== repro_ship_fix PASSED ===")


if __name__ == "__main__":
    main()
