"""Sentinel Resilience Score and operational metrics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.analytics.summary import load_scan_records


def _detection_precision(records: list[dict[str, Any]]) -> float:
    """Estimate precision: approved scans with corrections count as refined detections."""
    if not records:
        return 1.0

    scores: list[float] = []
    for record in records:
        findings = len(record.get("findings", []))
        if record.get("self_correction_triggered"):
            # Post-autopsy approved scan — high confidence after FP removal
            scores.append(0.92 if record.get("audit_status") == "approved" else 0.75)
        elif findings == 0:
            scores.append(1.0)
        else:
            scores.append(0.88)
    return round(sum(scores) / len(scores), 4)


def compute_resilience(project_root: Path | None = None) -> dict[str, Any]:
    """
    Sentinel Resilience Score =
      (Corrected False Positives / Total FP Attempts) + Detection Precision
    Normalized to 0–100 for dashboard display.
    """
    records = load_scan_records(project_root)

    fp_attempts = sum(
        1
        for r in records
        if r.get("self_correction_triggered") or r.get("retry_count", 0) > 0
    )
    corrected = sum(
        1
        for r in records
        if r.get("self_correction_triggered")
        and r.get("audit_status") == "approved"
    )

    fp_correction_rate = (corrected / fp_attempts) if fp_attempts else 1.0
    detection_precision = _detection_precision(records)

    raw_score = fp_correction_rate + detection_precision
    resilience_score = round(min(raw_score / 2, 1.0) * 100, 1)

    return {
        "resilience_score": resilience_score,
        "false_positive_correction_rate": round(fp_correction_rate, 4),
        "detection_precision": detection_precision,
        "false_positive_attempts": fp_attempts,
        "false_positives_corrected": corrected,
        "total_scans": len(records),
        "formula": "(Corrected FP / Total FP Attempts) + Detection Precision",
    }
