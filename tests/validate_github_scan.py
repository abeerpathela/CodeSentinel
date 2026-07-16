"""Validate GitHub remote repository ingestion and scan lifecycle."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

TEST_REPO = "https://github.com/abeerpathela/Taskly-.git"


def test_github_url_detection() -> None:
    from core.github_repo import GitHubManager

    assert GitHubManager.is_github_url(TEST_REPO)
    assert GitHubManager.is_github_url("https://github.com/user/repo")
    assert GitHubManager.is_github_url("github.com/user/repo")
    assert not GitHubManager.is_github_url(r"C:\local\path")
    print("[OK] GitHub URL regex detection")


def test_clone_scan_cleanup() -> None:
    if not os.getenv("GROQ_API_KEY"):
        print("[SKIP] GROQ_API_KEY not set — clone-only validation")
        return

    from backend.config.llm_config import LLMConfig
    from core.github_repo import GitHubManager
    from agents.mesh import run_mesh_scan

    manager = GitHubManager()
    cloned: Path | None = None
    try:
        cloned = manager.clone(TEST_REPO)
        assert cloned.is_dir(), "Clone directory missing"
        assert any(cloned.iterdir()), "Clone directory is empty"
        print(f"[OK] Cloned to {cloned}")

        config = LLMConfig()
        result = run_mesh_scan(str(cloned), config)
        assert result.get("scan_id"), "Scan did not return scan_id"
        assert result.get("files_scanned", 0) >= 0, "Scan did not complete Phase 2"
        print(
            f"[OK] Mesh scan complete: files={result.get('files_scanned')} "
            f"findings={len(result.get('findings', []))} "
            f"audit={result.get('audit_status')}"
        )

        from core.reporter import ReportEngine

        advisory = ReportEngine().save_sentinel_advisory(result)
        assert advisory.is_file(), "SENTINEL_ADVISORY not generated"
        print(f"[OK] SENTINEL_ADVISORY generated: {advisory.name}")
    finally:
        if cloned:
            assert cloned.exists(), "Clone path missing before cleanup"
            manager.cleanup(cloned)
            assert not cloned.exists(), "temp_scans directory was not deleted"
            print("[OK] temp_scans cleanup verified")


def test_api_invalid_github() -> None:
    from core.github_repo import GitHubManager, GitHubCloneError

    manager = GitHubManager()
    try:
        manager.clone("https://example.com/not-github")
    except GitHubCloneError as exc:
        assert exc.code == "invalid_url"
        print("[OK] Invalid URL rejected")
        return
    raise AssertionError("Expected GitHubCloneError for non-GitHub URL")


def main() -> None:
    print("=== validate_github_scan ===")
    test_github_url_detection()
    test_api_invalid_github()
    test_clone_scan_cleanup()
    print("\nGitHub ingestion validation passed.")


if __name__ == "__main__":
    main()
