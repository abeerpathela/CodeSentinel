"""Validate Phase 6 SSE UX flow and OAuth unauthorized handling."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STAGES = ["CLONING", "PARSING", "SBOM", "CODEBREAKER", "AUTOPSY", "CLEANUP", "COMPLETE"]


def test_progress_tracker_format() -> None:
    from backend.services.progress_stream import ProgressTracker

    tracker = ProgressTracker("test-scan")
    evt = tracker.event("CLONING", "Cloning repository...", status="active")
    assert evt["stage"] == "CLONING"
    assert evt["message"] == "Cloning repository..."
    assert evt["status"] == "active"
    line = ProgressTracker.sse_line(evt)
    assert line.startswith("data: ")
    parsed = json.loads(line.replace("data: ", "").strip())
    assert parsed["scan_id"] == "test-scan"
    print("[OK] ProgressTracker SSE JSON format")


def test_mock_sse_state_transitions() -> None:
    """Simulate full SSE stream and verify UI status transitions without freezing."""
    from backend.services.progress_stream import ProgressTracker

    tracker = ProgressTracker()
    ui_states: list[str] = []
    stages_seen: list[str] = []

    mock_stream = [
        tracker.event("CLONING", "Cloning repository...", status="active"),
        tracker.complete_stage("CLONING", "Clone complete."),
        tracker.event("PARSING", "Parsing filesystem...", status="active"),
        tracker.complete_stage("PARSING", "Parse complete."),
        tracker.complete_stage("SBOM", "SBOM built."),
        tracker.complete_stage("CODEBREAKER", "Scan complete."),
        tracker.event("AUTOPSY", "Auditing...", status="active"),
        tracker.complete_stage("AUTOPSY", "Audit complete."),
        tracker.complete_stage("CLEANUP", "Cleaned up."),
        tracker.complete_stage("COMPLETE", "Done.", outcome="secure", result={"findings": [], "sbom_risks": []}),
    ]

    for evt in mock_stream:
        ui = tracker.ui_scan_status(evt["stage"], evt["status"], evt.get("result"))
        ui_states.append(ui)
        stages_seen.append(evt["stage"])
        assert evt["stage"] in STAGES or evt["stage"] == "COMPLETE"

    assert "scanning" in ui_states
    assert "verifying" in ui_states or "scanning" in ui_states
    assert ui_states[-1] in ("secure", "breach")
    assert len(set(stages_seen)) >= 5
    print(f"[OK] Mock SSE transitions: {' -> '.join(ui_states)}")


def test_oauth_unauthorized() -> None:
    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    status = client.get("/auth/status")
    assert status.status_code == 200
    assert status.json()["authenticated"] is False

    deploy = client.post(
        "/deploy/ship",
        json={"repo_name": "test", "local_path": "/tmp/x"},
    )
    assert deploy.status_code == 401
    assert "Unauthorized" in deploy.json()["detail"]
    print("[OK] OAuth unauthorized handled for deploy without session")


def test_sse_endpoint_headers() -> None:
    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    fixture = ROOT / "fixtures" / "exploits" / "supply_chain"
    if not fixture.is_dir():
        print("[SKIP] SSE live test — fixture missing")
        return

    with client.stream(
        "POST",
        "/scan",
        json={"repo_path": str(fixture.resolve())},
        headers={"Accept": "text/event-stream"},
    ) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        chunks = []
        for line in resp.iter_lines():
            if line.startswith("data: "):
                chunks.append(json.loads(line[6:]))
            if chunks and chunks[-1].get("stage") == "COMPLETE":
                break
        assert len(chunks) >= 3
        assert any(c["stage"] == "SBOM" for c in chunks)
        print(f"[OK] Live SSE stream: {len(chunks)} events, final={chunks[-1]['stage']}")


def main() -> None:
    print("=== validate_ux_flow ===")
    test_progress_tracker_format()
    test_mock_sse_state_transitions()
    test_oauth_unauthorized()
    test_sse_endpoint_headers()
    print("\nPhase 6 UX flow validation passed.")


if __name__ == "__main__":
    main()
