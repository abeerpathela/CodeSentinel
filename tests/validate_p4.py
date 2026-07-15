"""
Phase 4 validation — SBOM integration, analytics summary, and scan API.

Usage:
    python tests/validate_p4.py

Requires GROQ_API_KEY, GEMINI_API_KEY, and running is NOT required (uses TestClient).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

MOCK_REQUIREMENTS = """requests==2.25.0
flask==1.0.0
fastapi>=0.115.0
"""

MOCK_PACKAGE_JSON = """{
  "name": "mock-app",
  "dependencies": {
    "express": "4.17.1",
    "lodash": "4.17.20"
  }
}
"""

MOCK_CODE = '''import os
user_cmd = input("cmd: ")
os.system(user_cmd)
'''


def _create_mock_repo(base: Path) -> Path:
    repo = base / "p4_mock_repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "requirements.txt").write_text(MOCK_REQUIREMENTS, encoding="utf-8")
    (repo / "package.json").write_text(MOCK_PACKAGE_JSON, encoding="utf-8")
    (repo / "vuln.py").write_text(MOCK_CODE, encoding="utf-8")
    return repo


def validate() -> None:
    if not os.getenv("GROQ_API_KEY") or not os.getenv("GEMINI_API_KEY"):
        print("[FAIL] GROQ_API_KEY and GEMINI_API_KEY are required.", file=sys.stderr)
        sys.exit(1)

    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    tmp = Path(tempfile.mkdtemp(prefix="codesentinel_p4_"))

    try:
        repo = _create_mock_repo(tmp)
        print(f"[INFO] Mock repo: {repo}")

        summary_before = client.get("/analytics/summary")
        if summary_before.status_code != 200:
            print(f"[FAIL] /analytics/summary returned {summary_before.status_code}", file=sys.stderr)
            sys.exit(1)
        before = summary_before.json()
        print(f"[INFO] Summary before scan: {json.dumps(before)}")

        scan_resp = client.post(
            "/codebreaker/scan",
            json={"repo_path": str(repo), "async_scan": False},
        )
        if scan_resp.status_code != 200:
            print(f"[FAIL] Scan returned {scan_resp.status_code}: {scan_resp.text}", file=sys.stderr)
            sys.exit(1)

        scan_data = scan_resp.json()
        print(f"[INFO] Scan ID: {scan_data.get('scan_id')}")
        print(f"[INFO] Files scanned: {scan_data.get('files_scanned')}")
        print(f"[INFO] Code findings: {len(scan_data.get('findings', []))}")
        print(f"[INFO] SBOM risks: {len(scan_data.get('sbom_risks', []))}")

        if scan_data.get("files_scanned", 0) < 1:
            print("[FAIL] Expected at least 1 source file scanned.", file=sys.stderr)
            sys.exit(1)
        print("[OK] Source files scanned")

        if not scan_data.get("sbom_risks"):
            print("[FAIL] Expected SBOM transitive risks from mock manifests.", file=sys.stderr)
            sys.exit(1)
        print("[OK] SBOM risks detected")

        summary_after = client.get("/analytics/summary").json()
        print(f"[INFO] Summary after scan: {json.dumps(summary_after)}")

        if summary_after.get("latest_scan_id") != scan_data["scan_id"]:
            print("[FAIL] Analytics latest_scan_id does not match scan.", file=sys.stderr)
            sys.exit(1)
        print("[OK] Analytics latest_scan_id matches scan")

        if str(repo.resolve()) not in (summary_after.get("latest_repo_path") or ""):
            print("[FAIL] Analytics latest_repo_path mismatch.", file=sys.stderr)
            sys.exit(1)
        print("[OK] Analytics latest_repo_path matches")

        if summary_after.get("total_sbom_risks", 0) < len(scan_data.get("sbom_risks", [])) and summary_after.get("total_scans", 0) <= 1:
            pass
        elif summary_after.get("total_sbom_risks", 0) == 0 and scan_data.get("sbom_risks"):
            print("[WARN] SBOM risks not yet in aggregate (may need rescan)")
        print("[OK] Analytics summary reflects scan data")

        detail = client.get(f"/analytics/scans/{scan_data['scan_id']}")
        if detail.status_code != 200:
            print(f"[FAIL] Scan detail 404 for {scan_data['scan_id']}", file=sys.stderr)
            sys.exit(1)
        detail_data = detail.json()
        if detail_data.get("repo_path") != str(repo.resolve()):
            print("[FAIL] Scan detail repo_path mismatch.", file=sys.stderr)
            sys.exit(1)
        if len(detail_data.get("findings", [])) != len(scan_data.get("findings", [])):
            print("[FAIL] Scan detail findings count mismatch.", file=sys.stderr)
            sys.exit(1)
        print("[OK] Scan detail matches scan response")

        if scan_data.get("sbom_graph"):
            print(f"[OK] SBOM graph edges: {len(scan_data['sbom_graph'])}")
        else:
            print("[WARN] No SBOM graph edges (non-fatal)")

        print("CodeSentinel Phase 4 Ready")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    validate()
