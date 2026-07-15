"""Analytics aggregation from scan history."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_scan_records(project_root: Path | None = None) -> list[dict[str, Any]]:
    root = project_root or Path(__file__).resolve().parents[1]
    scans_dir = root / "logs" / "scans"
    if not scans_dir.is_dir():
        return []

    records: list[dict[str, Any]] = []
    for path in sorted(scans_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return records


def compute_summary(project_root: Path | None = None) -> dict[str, Any]:
    records = load_scan_records(project_root)
    total_files = sum(r.get("files_scanned", 0) for r in records)
    total_vulns = sum(len(r.get("findings", [])) for r in records)
    total_sbom_risks = sum(len(r.get("sbom_risks", [])) for r in records)

    corrections = sum(
        1
        for r in records
        if r.get("retry_count", 0) > 0 or r.get("self_correction_triggered")
    )
    scans_with_corrections = sum(1 for r in records if r.get("memory_stored"))

    autopsy_win_rate = (
        round(corrections / len(records) * 100, 1) if records else 0.0
    )

    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for record in records:
        for finding in record.get("findings", []):
            sev = finding.get("severity", "Low")
            if sev in severity_counts:
                severity_counts[sev] += 1
            elif sev.lower() == "critical":
                severity_counts["Critical"] += 1
        for risk in record.get("sbom_risks", []):
            sev = risk.get("risk_level", "Low")
            if sev in severity_counts:
                severity_counts[sev] += 1

    latest = records[-1] if records else None

    return {
        "total_scans": len(records),
        "total_files_scanned": total_files,
        "total_vulnerabilities_caught": total_vulns + total_sbom_risks,
        "total_code_findings": total_vulns,
        "total_sbom_risks": total_sbom_risks,
        "total_self_corrections": corrections,
        "autopsy_win_rate_pct": autopsy_win_rate,
        "memory_corrections_stored": scans_with_corrections,
        "severity_breakdown": severity_counts,
        "latest_scan_id": latest.get("scan_id") if latest else None,
        "latest_repo_path": latest.get("repo_path") if latest else None,
    }
