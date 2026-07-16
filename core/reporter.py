"""Enterprise Security Audit Report generation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.analytics.metrics import compute_resilience
from backend.analytics.summary import compute_summary, load_scan_records


class ReportEngine:
    """Aggregates Codebreaker, Autopsy, and SBOM data into audit reports."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.root = project_root or Path(__file__).resolve().parents[1]
        self.reports_dir = self.root / "logs" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _blast_radius(self, risk: dict[str, Any]) -> int:
        base = {"Critical": 95, "High": 75, "Medium": 50, "Low": 25}
        score = base.get(risk.get("risk_level", "Low"), 30)
        if risk.get("transitive_of"):
            score += 10
        return min(score, 100)

    def aggregate(self, scan_ids: list[str] | None = None) -> dict[str, Any]:
        records = load_scan_records(self.root)
        if scan_ids:
            records = [r for r in records if r.get("scan_id") in scan_ids]

        all_findings: list[dict] = []
        all_sbom: list[dict] = []
        corrections = 0
        fp_suppressed = 0

        for record in records:
            all_findings.extend(record.get("findings", []))
            all_sbom.extend(record.get("sbom_risks", []))
            if record.get("self_correction_triggered"):
                corrections += 1
                fp_suppressed += max(0, record.get("retry_count", 0))

        summary = compute_summary(self.root)
        resilience = compute_resilience(self.root)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scans_included": len(records),
            "total_vulnerabilities": len(all_findings) + len(all_sbom),
            "code_findings": len(all_findings),
            "sbom_risks": len(all_sbom),
            "autopsy_corrections": corrections,
            "false_positives_suppressed": fp_suppressed,
            "resilience_gain_pct": resilience.get("resilience_score", 0),
            "findings": all_findings,
            "sbom_risks_detail": all_sbom,
            "summary": summary,
            "resilience": resilience,
            "scan_records": records,
        }

    def render_markdown(self, data: dict[str, Any] | None = None) -> str:
        data = data or self.aggregate()
        ts = data["generated_at"][:19].replace("T", " ")

        lines = [
            "# CodeSentinel Security Audit Report",
            "",
            f"**Generated:** {ts} UTC  ",
            f"**Classification:** CONFIDENTIAL — Internal Security Assessment",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Scans Analyzed | {data['scans_included']} |",
            f"| Total Vulnerabilities Detected | {data['total_vulnerabilities']} |",
            f"| Code Findings (Codebreaker) | {data['code_findings']} |",
            f"| SBOM Supply-Chain Risks | {data['sbom_risks']} |",
            f"| Autopsy Self-Corrections | {data['autopsy_corrections']} |",
            f"| False Positives Suppressed | {data['false_positives_suppressed']} |",
            f"| Sentinel Resilience Score | {data['resilience_gain_pct']}% |",
            "",
            "## Resilience Gain (Autopsy)",
            "",
            f"The Autopsy auditor (Groq Llama 3.3) performed **{data['autopsy_corrections']}** "
            f"self-correction cycle(s), suppressing **{data['false_positives_suppressed']}** "
            f"false-positive finding(s) before final approval.",
            "",
            f"- **Detection Precision:** {data['resilience'].get('detection_precision', 0):.2%}",
            f"- **FP Correction Rate:** {data['resilience'].get('false_positive_correction_rate', 0):.2%}",
            "",
            "## Codebreaker Findings",
            "",
        ]

        if not data["findings"]:
            lines.append("_No code vulnerabilities recorded in selected scans._")
        else:
            lines.append("| Severity | File | Type | Description |")
            lines.append("|----------|------|------|-------------|")
            for f in data["findings"]:
                desc = str(f.get("description", "")).replace("|", "/")[:80]
                lines.append(
                    f"| {f.get('severity', 'Low')} | `{f.get('file_path', '?')}` | "
                    f"{f.get('vulnerability_type', '?')} | {desc} |"
                )

        lines.extend(["", "## SBOM Dependency Risk Scores", ""])

        if not data["sbom_risks_detail"]:
            lines.append("_No supply-chain risks detected._")
        else:
            lines.append("| Package | Version | Risk | Blast Radius | Notes |")
            lines.append("|---------|---------|------|--------------|-------|")
            for r in data["sbom_risks_detail"]:
                br = self._blast_radius(r)
                notes = str(r.get("notes", "")).replace("|", "/")[:60]
                lines.append(
                    f"| {r.get('name', '?')} | {r.get('version', '?')} | "
                    f"{r.get('risk_level', 'Low')} | {br} | {notes} |"
                )

        lines.extend(
            [
                "",
                "---",
                "",
                "*Report generated by CodeSentinel ReportEngine v1.0*",
                "*Models: gemini-2.5-flash (Codebreaker) · llama-3.3-70b-versatile (Autopsy)*",
            ]
        )
        return "\n".join(lines)

    def generate_and_save(
        self, scan_ids: list[str] | None = None, *, filename: str | None = None
    ) -> Path:
        data = self.aggregate(scan_ids)
        markdown = self.render_markdown(data)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_name = filename or f"security_audit_{stamp}.md"
        out_path = self.reports_dir / out_name
        out_path.write_text(markdown, encoding="utf-8")
        return out_path

    def render_sentinel_advisory(self, scan_record: dict[str, Any]) -> str:
        """Per-scan SENTINEL_ADVISORY executive summary."""
        scan_id = scan_record.get("scan_id", "unknown")
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        findings = scan_record.get("findings", [])
        sbom = scan_record.get("sbom_risks", [])
        total = len(findings) + len(sbom)
        critical = sum(
            1
            for f in findings + sbom
            for sev in [f.get("severity", f.get("risk_level", ""))]
            if str(sev).lower() == "critical"
        )

        lines = [
            "# SENTINEL ADVISORY",
            "",
            f"**Scan ID:** `{scan_id}`  ",
            f"**Generated:** {ts}  ",
            f"**Target:** `{scan_record.get('repo_path', 'unknown')}`  ",
            f"**Classification:** CONFIDENTIAL",
            "",
            "## Executive Summary",
            "",
            f"- **Total Threats:** {total}",
            f"- **Critical Severity:** {critical}",
            f"- **Files Scanned:** {scan_record.get('files_scanned', 0)}",
            f"- **Autopsy Self-Correction:** {'Yes' if scan_record.get('self_correction_triggered') else 'No'}",
            f"- **Audit Status:** {scan_record.get('audit_status', 'approved')}",
            "",
            "## Codebreaker Findings",
            "",
        ]
        if not findings:
            lines.append("_No code vulnerabilities detected._")
        else:
            for f in findings:
                lines.append(
                    f"- **{f.get('severity', '?')}** — `{f.get('file_path', '?')}`: "
                    f"{f.get('vulnerability_type', '?')} — {f.get('description', '')[:120]}"
                )

        lines.extend(["", "## Supply Chain (SBOM)", ""])
        if not sbom:
            lines.append("_No SBOM risks detected._")
        else:
            for r in sbom:
                lines.append(
                    f"- **{r.get('risk_level', '?')}** — {r.get('name', '?')} "
                    f"{r.get('version', '')}: {r.get('notes', '')[:80]}"
                )

        lines.extend(
            [
                "",
                "---",
                "*SENTINEL_ADVISORY — CodeSentinel ReportEngine*",
                "*Models: gemini-2.5-flash · llama-3.3-70b-versatile*",
            ]
        )
        return "\n".join(lines)

    def save_sentinel_advisory(self, scan_record: dict[str, Any]) -> Path:
        scan_id = scan_record.get("scan_id", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        markdown = self.render_sentinel_advisory(scan_record)
        out_path = self.reports_dir / f"SENTINEL_ADVISORY_{scan_id}.md"
        out_path.write_text(markdown, encoding="utf-8")
        return out_path
