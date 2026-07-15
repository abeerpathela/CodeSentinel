"""Prune old scan and trace logs to prevent unbounded growth."""

from __future__ import annotations

from pathlib import Path

MAX_SCAN_HISTORY = 10


def prune_logs(project_root: Path | None = None, *, max_keep: int = MAX_SCAN_HISTORY) -> dict[str, int]:
    """Keep only the most recent scan/trace files."""
    root = project_root or Path(__file__).resolve().parents[1]
    removed = {"scans": 0, "traces": 0}

    for subdir, key in (("scans", "scans"), ("traces", "traces")):
        folder = root / "logs" / subdir
        if not folder.is_dir():
            continue
        files = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[max_keep:]:
            old.unlink(missing_ok=True)
            removed[key] += 1

    return removed
