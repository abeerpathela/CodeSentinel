"""In-memory scan progress store for dashboard polling."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any


class ScanStatusStore:
    """Thread-safe store for live Autopsy feed polling."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._scans: dict[str, dict[str, Any]] = {}

    def create(self, scan_id: str, repo_path: str) -> None:
        with self._lock:
            self._scans[scan_id] = {
                "scan_id": scan_id,
                "repo_path": repo_path,
                "status": "queued",
                "feed": [],
                "result": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

    def push(self, scan_id: str, message: str, *, stage: str | None = None) -> None:
        with self._lock:
            entry = self._scans.get(scan_id)
            if not entry:
                return
            entry["feed"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": message,
                    "stage": stage or entry.get("status", ""),
                }
            )
            if stage:
                entry["status"] = stage
            entry["updated_at"] = datetime.now(timezone.utc).isoformat()

    def complete(self, scan_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            entry = self._scans.get(scan_id)
            if not entry:
                return
            entry["status"] = "complete"
            entry["result"] = result
            entry["feed"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": "Scan complete.",
                    "stage": "complete",
                }
            )
            entry["updated_at"] = datetime.now(timezone.utc).isoformat()

    def fail(self, scan_id: str, error: str) -> None:
        with self._lock:
            entry = self._scans.get(scan_id)
            if not entry:
                return
            entry["status"] = "error"
            entry["feed"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": f"Error: {error}",
                    "stage": "error",
                }
            )
            entry["updated_at"] = datetime.now(timezone.utc).isoformat()

    def get(self, scan_id: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._scans.get(scan_id)
            return dict(entry) if entry else None


scan_status_store = ScanStatusStore()
