"""SSE progress streaming for live scan experiences."""

from __future__ import annotations

import json
from collections.abc import Generator, Iterator
from datetime import datetime, timezone
from typing import Any, Literal

ProgressStatus = Literal["active", "done", "error"]

STAGE_ORDER = (
    "CLONING",
    "PARSING",
    "SBOM",
    "CODEBREAKER",
    "AUTOPSY",
    "CLEANUP",
    "COMPLETE",
)


class ProgressTracker:
    """Yield structured JSON progress events for SSE clients."""

    def __init__(self, scan_id: str | None = None) -> None:
        self.scan_id = scan_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._completed: set[str] = set()

    def event(
        self,
        stage: str,
        message: str,
        *,
        status: ProgressStatus = "active",
        reasoning: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "scan_id": self.scan_id,
            "stage": stage.upper(),
            "message": message,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if reasoning:
            payload["reasoning"] = reasoning
        if status == "done":
            self._completed.add(stage.upper())
        payload.update(extra)
        return payload

    def complete_stage(self, stage: str, message: str, **extra: Any) -> dict[str, Any]:
        return self.event(stage, message, status="done", **extra)

    def error(self, stage: str, message: str, **extra: Any) -> dict[str, Any]:
        return self.event(stage, message, status="error", **extra)

    @staticmethod
    def sse_line(data: dict[str, Any]) -> str:
        return f"data: {json.dumps(data, default=str)}\n\n"

    def stream_wrap(self, events: Iterator[dict[str, Any]]) -> Generator[str, None, None]:
        """Convert progress dicts into SSE wire format."""
        for item in events:
            yield self.sse_line(item)

    def ui_scan_status(self, stage: str, status: ProgressStatus, result: dict | None = None) -> str:
        """Map backend stage to frontend orb scanStatus."""
        if status == "error":
            return "breach"
        stage_u = stage.upper()
        if status == "done" and stage_u == "COMPLETE":
            if not result:
                return "idle"
            threats = len(result.get("findings", [])) + len(result.get("sbom_risks", []))
            return "breach" if threats > 0 else "secure"
        mapping = {
            "CLONING": "scanning",
            "PARSING": "scanning",
            "SBOM": "scanning",
            "CODEBREAKER": "scanning",
            "AUTOPSY": "verifying",
            "CLEANUP": "scanning",
        }
        return mapping.get(stage_u, "scanning")
