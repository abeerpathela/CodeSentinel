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
TEST_SCAN_ID = "github_validate_scan_001"


def test_github_url_detection() -> None:
    from core.github_handler import GitHubHandler

    assert GitHubHandler.is_github_url(TEST_REPO)
    assert not GitHubHandler.is_github_url(r"C:\local\path")
    print("[OK] GitHub URL regex detection")


def test_clone_scan_retention() -> None:
    if not os.getenv("GROQ_API_KEY"):
        print("[SKIP] GROQ_API_KEY not set")
        return

    from backend.config.path_config import resolve_scan_path
    from backend.config.llm_config import LLMConfig
    from backend.services.scan_session import register_workspace
    from agents.mesh import run_mesh_scan
    from core.github_handler import GitHubHandler

    handler = GitHubHandler()
    scan_id = TEST_SCAN_ID
    dest = resolve_scan_path(scan_id)
    if dest.exists():
        handler.cleanup(dest)

    cloned = handler.clone_repository(TEST_REPO, scan_id)
    rel = cloned.relative_to(ROOT)
    print(f"[OK] Cloned to {rel.as_posix()}")
    assert cloned.name == scan_id

    register_workspace(scan_id)
    config = LLMConfig()
    result = run_mesh_scan(str(cloned), config, scan_id=scan_id)
    assert result.get("scan_id") == scan_id
    print(f"[OK] Mesh scan: files={result.get('files_scanned')} findings={len(result.get('findings', []))}")

    assert dest.is_dir(), "workspace should remain for deploy TTL"
    handler.cleanup(dest)
    assert not dest.exists()
    print("[OK] Manual cleanup verified")


def main() -> None:
    print("=== validate_github_scan ===")
    test_github_url_detection()
    test_clone_scan_retention()
    print("\nGitHub ingestion validation passed.")


if __name__ == "__main__":
    main()
