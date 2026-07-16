"""Validate remote GitHub scan via POST /scan API."""

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
TEMP_ROOT = ROOT / "backend" / "data" / "temp_scans"


def _list_clone_dirs() -> set[str]:
    if not TEMP_ROOT.is_dir():
        return set()
    return {p.name for p in TEMP_ROOT.iterdir() if p.is_dir()}


def main() -> None:
    if not os.getenv("GROQ_API_KEY"):
        print("[FAIL] GROQ_API_KEY required for mesh scan.", file=sys.stderr)
        sys.exit(1)

    from fastapi.testclient import TestClient

    from backend.main import app
    from core.github_handler import GitHubHandler

    GitHubHandler.ensure_temp_root(ROOT)
    before = _list_clone_dirs()

    print(f"[INFO] Submitting remote scan: {TEST_REPO}")
    print(f"[INFO] temp_scans before: {len(before)} dir(s)")

    client = TestClient(app)
    response = client.post(
        "/scan/sync",
        json={"repo_path": TEST_REPO, "async_scan": False},
    )

    print(f"[INFO] HTTP status: {response.status_code}")
    if response.status_code != 200:
        print(f"[FAIL] Body: {response.text}", file=sys.stderr)
        sys.exit(1)

    data = response.json()
    findings = data.get("findings", [])
    sbom = data.get("sbom_risks", [])
    files = data.get("files_scanned", 0)
    total_threats = len(findings) + len(sbom)

    print(f"[INFO] files_scanned={files} findings={len(findings)} sbom_risks={len(sbom)}")
    print(f"[INFO] audit_status={data.get('audit_status')} scan_id={data.get('scan_id')}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert files > 0, "Scan did not ingest repository files"
    assert total_threats > 0, "Expected scanned vulnerabilities (findings or SBOM risks)"

    after = _list_clone_dirs()
    new_dirs = after - before
    print(f"[INFO] temp_scans after: {len(after)} dir(s), new={new_dirs or 'none'}")

    assert not new_dirs, f"Temporary clone(s) not cleaned up: {new_dirs}"
    print("[OK] temp_scans/[uuid] removed after scan")

    feed_stages = []
    scan_id = data.get("scan_id")
    if scan_id:
        status = client.get(f"/scan/{scan_id}/status")
        if status.status_code == 200:
            feed = status.json().get("feed", [])
            feed_stages = [e.get("message", "") for e in feed]
            for msg in feed_stages:
                if "🛰️" in msg or "📥" in msg or "✅" in msg or "🧹" in msg:
                    print(f"[FEED] {msg}")

    print("\n=== validate_remote_scan PASSED ===")
    print(f"  Repository: {TEST_REPO}")
    print(f"  Files scanned: {files}")
    print(f"  Vulnerabilities: {total_threats} ({len(findings)} code + {len(sbom)} SBOM)")
    print(f"  Temp workspace cleaned: yes")


if __name__ == "__main__":
    main()
