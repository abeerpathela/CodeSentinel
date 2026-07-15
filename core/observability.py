"""Reasoning trace capture for Autopsy root-cause analysis."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TraceLogger:
    """Persists LLM inputs, outputs, and reasoning paths per scan."""

    def __init__(self, scan_id: str, *, traces_dir: Path | None = None) -> None:
        self.scan_id = scan_id
        self.traces_dir = traces_dir or (
            Path(__file__).resolve().parents[1] / "logs" / "traces"
        )
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.traces_dir / f"{scan_id}.json"
        self._events: list[dict[str, Any]] = []
        self._started_at = datetime.now(timezone.utc).isoformat()

    def log_llm_call(
        self,
        *,
        agent: str,
        model: str,
        llm_input: Any,
        llm_output: str,
        reasoning_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record one LLM exchange with its thought process."""
        self._events.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": agent,
                "model": model,
                "llm_input": llm_input,
                "llm_output": llm_output,
                "reasoning_path": reasoning_path,
                "metadata": metadata or {},
            }
        )

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Record a non-LLM mesh event (audit decision, retry, memory store)."""
        self._events.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                **payload,
            }
        )

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def save(self) -> Path:
        """Write the full trace file for this scan."""
        document = {
            "scan_id": self.scan_id,
            "started_at": self._started_at,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "event_count": len(self._events),
            "events": self._events,
        }
        self.path.write_text(json.dumps(document, indent=2), encoding="utf-8")
        return self.path
