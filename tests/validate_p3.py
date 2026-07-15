"""
Phase 3 validation — RCE false-positive regression (safe_subprocess.py).

Usage:
    python tests/validate_p3.py

Requires GROQ_API_KEY and GEMINI_API_KEY in .env at project root.
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

SAFE_SUBPROCESS = '''import subprocess

def get_python_version():
    return subprocess.run(["python", "--version"], capture_output=True, text=True, shell=False).stdout
'''


def _create_fixture_repo(base: Path) -> Path:
    repo = base / "p3_fixture"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "safe_subprocess.py").write_text(SAFE_SUBPROCESS, encoding="utf-8")
    return repo


def _has_rce_finding(findings: list[dict]) -> bool:
    for f in findings:
        vtype = f.get("vulnerability_type", "").lower()
        if "remote command" in vtype or "rce" in vtype or "command execution" in vtype:
            return True
    return False


def validate() -> None:
    from agents.mesh import run_mesh_scan
    from backend.config.llm_config import LLMConfig
    from core.memory import STANDARD_PRACTICE_RCE_ID, STANDARD_PRACTICE_RCE_TEXT, VectorMemory

    if not os.getenv("GROQ_API_KEY") or not os.getenv("GEMINI_API_KEY"):
        print("[FAIL] GROQ_API_KEY and GEMINI_API_KEY are required.", file=sys.stderr)
        sys.exit(1)

    config = LLMConfig()
    memory = VectorMemory()
    memory.ensure_standard_practices()

    tmp = Path(tempfile.mkdtemp(prefix="codesentinel_p3_"))
    try:
        repo = _create_fixture_repo(tmp)
        print(f"[INFO] Fixture repo: {repo}")

        result = run_mesh_scan(
            str(repo),
            config,
            seed_test_false_positive=True,
        )

        final = result.get("findings", [])
        initial = result.get("initial_findings", [])

        print(f"[INFO] Audit status: {result.get('audit_status')}")
        print(f"[INFO] Retry count: {result.get('retry_count')}")
        print(f"[INFO] Self-correction triggered: {result.get('self_correction_triggered')}")
        print(f"[INFO] Trace file: {result.get('trace_file')}")
        print(f"[INFO] Initial findings: {len(initial)} | Final findings: {len(final)}")
        print(f"[INFO] Final findings JSON: {json.dumps(final)}")

        if _has_rce_finding(final):
            print(
                "[FAIL] Final findings still contain RCE on safe_subprocess.py",
                file=sys.stderr,
            )
            sys.exit(1)
        print("[OK] No RCE finding on safe_subprocess.py after Autopsy loop")

        if not result.get("self_correction_triggered"):
            print("[FAIL] Self-correction loop was not triggered.", file=sys.stderr)
            sys.exit(1)
        print("[OK] Self-correction loop triggered")

        if result.get("retry_count") != 1:
            print(
                f"[FAIL] Expected retry_count=1, got {result.get('retry_count')}",
                file=sys.stderr,
            )
            sys.exit(1)
        print("[OK] retry_count=1 confirmed")

        trace_path = Path(result.get("trace_file", ""))
        if not trace_path.is_file():
            print("[FAIL] Trace file not written.", file=sys.stderr)
            sys.exit(1)

        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        rejected = [
            e for e in trace.get("events", []) if e.get("event_type") == "audit_rejected"
        ]
        if not rejected:
            print("[FAIL] Trace missing audit_rejected event.", file=sys.stderr)
            sys.exit(1)

        audit_rationale = rejected[0].get("audit_rationale", "")
        if not audit_rationale:
            print("[FAIL] Trace missing audit_rationale on rejection.", file=sys.stderr)
            sys.exit(1)
        print(f"[OK] audit_rationale present: {audit_rationale[:120]}...")

        complete = [
            e for e in trace.get("events", []) if e.get("event_type") == "scan_complete"
        ]
        if complete and complete[-1].get("retry_count") != 1:
            print("[FAIL] scan_complete event retry_count != 1.", file=sys.stderr)
            sys.exit(1)
        print("[OK] Trace shows retry_count=1 on scan_complete")

        practice = memory.get_by_id(STANDARD_PRACTICE_RCE_ID)
        if not practice:
            print("[FAIL] Standard practice memory not found in ChromaDB.", file=sys.stderr)
            sys.exit(1)
        if STANDARD_PRACTICE_RCE_TEXT not in practice.get("document", ""):
            print("[FAIL] Fixed-arg RCE rule not stored in vector memory.", file=sys.stderr)
            sys.exit(1)
        print(f"[OK] Vector memory contains Fixed Arg rule: {STANDARD_PRACTICE_RCE_TEXT}")

        print("CodeSentinel Phase 3 RCE Regression Passed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    validate()
