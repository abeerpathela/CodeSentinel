"""Validate remote GitHub scan via POST /scan/sync API."""

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


def main() -> None:
    if not os.getenv("GROQ_API_KEY"):
        print("[FAIL] GROQ_API_KEY required.", file=sys.stderr)
        sys.exit(1)

    from fastapi.testclient import TestClient

    from backend.config.path_config import resolve_scan_path
    from backend.main import app

    client = TestClient(app)
    print(f"[INFO] Submitting remote scan: {TEST_REPO}")

    response = client.post(
        "/scan/sync",
        json={"repo_path": TEST_REPO, "async_scan": False},
    )

    print(f"[INFO] HTTP status: {response.status_code}")
    if response.status_code != 200:
        print(f"[FAIL] Body: {response.text}", file=sys.stderr)
        sys.exit(1)

    data = response.json()
    scan_id = data.get("scan_id")
    findings = data.get("findings", [])
    sbom = data.get("sbom_risks", [])
    files = data.get("files_scanned", 0)
    total_threats = len(findings) + len(sbom)

    workspace = resolve_scan_path(scan_id)
    rel = workspace.relative_to(ROOT)
    print(f"[INFO] scan_id={scan_id} files={files} threats={total_threats}")
    print(f"[INFO] workspace retained at {rel.as_posix()}")

    assert workspace.is_dir(), "scan workspace should be retained for deploy"
    assert data.get("repo_path") == scan_id, "API should expose scan_id as repo_path reference"
    assert files > 0 and total_threats > 0

    print("[OK] Workspace retained under scan_id for Ship-to-GitHub")
    print("\n=== validate_remote_scan PASSED ===")


if __name__ == "__main__":
    main()
