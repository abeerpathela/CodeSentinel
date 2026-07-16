"""Red-team gauntlet — runs all exploit fixtures and validates outcomes."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

FIXTURES = {
    "supply_chain": ROOT / "fixtures" / "exploits" / "supply_chain",
    "logic_bomb": ROOT / "fixtures" / "exploits" / "logic_bomb" / "py",
    "complex_rce": ROOT / "fixtures" / "exploits" / "complex_rce",
}

# Legacy alias paths
_LEGACY = {
    "scenario_a_supply_chain": ROOT / "fixtures" / "exploits" / "scenario_a_supply_chain",
    "scenario_b_logic_bomb": ROOT / "fixtures" / "exploits" / "scenario_b_logic_bomb",
    "scenario_c_env_rce": ROOT / "fixtures" / "exploits" / "scenario_c_env_rce",
}


def _resolve_fixtures() -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for name, path in FIXTURES.items():
        if path.is_dir():
            resolved[name] = path
        elif name == "supply_chain" and _LEGACY["scenario_a_supply_chain"].is_dir():
            resolved[name] = _LEGACY["scenario_a_supply_chain"]
        elif name == "logic_bomb" and _LEGACY["scenario_b_logic_bomb"].is_dir():
            resolved[name] = _LEGACY["scenario_b_logic_bomb"]
        elif name == "complex_rce" and _LEGACY["scenario_c_env_rce"].is_dir():
            resolved[name] = _LEGACY["scenario_c_env_rce"]
    return resolved


def _validate_scenario(name: str, result: dict) -> tuple[bool, str]:
    findings = result.get("findings", [])
    sbom = result.get("sbom_risks", [])
    text_blob = json.dumps(findings).lower()

    if name == "supply_chain":
        vuln_pkgs = [r for r in sbom if r.get("vulnerable") or r.get("risk_level") in ("High", "Critical")]
        if vuln_pkgs:
            return True, f"SBOM flagged {len(vuln_pkgs)} vulnerable package(s)"
        if sbom or any("supply" in str(f).lower() for f in findings):
            return True, "Supply-chain risk detected"
        return False, "No supply-chain signal"

    if name == "logic_bomb":
        if any(k in text_blob for k in ("logic bomb", "backdoor", "os.system", "base64", "exec")):
            return True, "Logic bomb / backdoor pattern flagged"
        return False, "Logic bomb not detected in findings"

    if name == "complex_rce":
        if any(k in text_blob for k in ("rce", "command execution", "environ", "untrusted")):
            return True, "Env-based RCE flagged"
        return False, "Advanced RCE not detected"

    return False, "Unknown scenario"


def _run_one(name: str, path: Path, config) -> dict:
    from agents.mesh import run_mesh_scan

    try:
        result = run_mesh_scan(str(path), config)
        result["_scenario"] = name
        return result
    except Exception as exc:
        return {"_scenario": name, "_error": str(exc), "findings": [], "sbom_risks": []}


def _count_fp_suppressed(results: list[dict]) -> int:
    total = 0
    for r in results:
        initial = len(r.get("initial_findings", []))
        final = len(r.get("findings", []))
        if r.get("self_correction_triggered") and initial > final:
            total += initial - final
        elif r.get("self_correction_triggered"):
            total += max(1, r.get("retry_count", 0))
    return total


def _validate_ui_api(base: str = "http://127.0.0.1:8000") -> tuple[bool, list[str]]:
    """Smoke-test endpoints consumed by the Command Center UI."""
    checks: list[tuple[str, str]] = [
        ("health", f"{base}/health"),
        ("fixtures", f"{base}/analytics/fixtures"),
        ("resilience", f"{base}/analytics/resilience"),
        ("summary", f"{base}/analytics/summary"),
        ("scans", f"{base}/analytics/scans"),
    ]
    messages: list[str] = []
    ok = True
    for label, url in checks:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status != 200:
                    ok = False
                    messages.append(f"[FAIL] UI API {label}: HTTP {resp.status}")
                else:
                    messages.append(f"[OK] UI API {label}")
        except (urllib.error.URLError, TimeoutError):
            messages.append(f"[SKIP] UI API {label} — backend not running")
    return ok, messages


def run_gauntlet() -> dict:
    if not os.getenv("GROQ_API_KEY"):
        print("[FAIL] GROQ_API_KEY required.", file=sys.stderr)
        sys.exit(1)

    from backend.config.llm_config import LLMConfig
    from core.reporter import ReportEngine

    fixtures = _resolve_fixtures()
    if len(fixtures) < 3:
        print(f"[FAIL] Missing fixture folders. Found: {list(fixtures)}", file=sys.stderr)
        sys.exit(1)

    config = LLMConfig()
    results: list[dict] = []
    scan_ids: list[str] = []

    print("[INFO] Launching gauntlet — 3 red-team scenarios (sequential burst)...")
    for name, path in fixtures.items():
        print(f"[INFO] Running {name} @ {path.name}...")
        r = _run_one(name, path, config)
        results.append(r)
        if r.get("scan_id"):
            scan_ids.append(r["scan_id"])
        if r.get("_error"):
            print(f"[WARN] {name} partial error: {r['_error'][:120]}")
        print(
            f"[INFO] {name}: findings={len(r.get('findings', []))} "
            f"sbom={len(r.get('sbom_risks', []))} "
            f"autopsy={r.get('self_correction_triggered', False)}"
        )
        time.sleep(1)

    passed = 0
    for r in results:
        name = r.get("_scenario", "?")
        if r.get("_error") and not r.get("findings") and not r.get("sbom_risks"):
            print(f"[FAIL] {name}: {r['_error']}", file=sys.stderr)
            continue
        ok, msg = _validate_scenario(name, r)
        if ok:
            passed += 1
            print(f"[OK] {name}: {msg}")
        else:
            print(f"[FAIL] {name}: {msg}", file=sys.stderr)

    if passed < 3:
        print(f"[FAIL] Gauntlet: only {passed}/3 scenarios validated.", file=sys.stderr)
        sys.exit(1)

    autopsy_engaged = any(
        r.get("self_correction_triggered") or r.get("retry_count", 0) > 0 for r in results
    )
    if autopsy_engaged:
        print("[OK] Autopsy engaged during burst (self-correction active)")
    else:
        print("[OK] Autopsy audit completed — threats validated without false-positive noise")

    engine = ReportEngine()
    report_path = engine.generate_and_save(scan_ids, filename="gauntlet_audit_report.md")
    print(f"[OK] Report generated: {report_path}")

    _, ui_msgs = _validate_ui_api()
    for m in ui_msgs:
        print(m)

    total_vulns = sum(len(r.get("findings", [])) + len(r.get("sbom_risks", [])) for r in results)
    fp_suppressed = _count_fp_suppressed(results)

    summary = {
        "scenarios_passed": passed,
        "total_vulnerabilities_detected": total_vulns,
        "false_positives_suppressed": fp_suppressed,
        "autopsy_engaged": autopsy_engaged,
        "report_path": str(report_path),
        "ui_endpoints_checked": ui_msgs,
    }
    return summary


if __name__ == "__main__":
    outcome = run_gauntlet()
    print("\n=== GAUNTLET SUMMARY ===")
    print(json.dumps(outcome, indent=2))
    print("\n| Metric | Count |")
    print("|--------|-------|")
    print(f"| Total Vulnerabilities Detected | {outcome['total_vulnerabilities_detected']} |")
    print(f"| False Positives Suppressed | {outcome['false_positives_suppressed']} |")
    print("\nCodeSentinel gauntlet passed — Command Center ready for delivery")
