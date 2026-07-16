"""Generator-based scan pipeline with SSE progress yields."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

from agents.mesh import run_mesh_scan
from backend.config.llm_config import LLMConfig
from backend.services.progress_stream import ProgressTracker
from core.github_handler import GitHubCloneError, GitHubHandler
from core.reporter import ReportEngine

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def iter_scan(repo_input: str, llm_config: LLMConfig) -> Generator[dict[str, Any], None, None]:
    """Yield progress events through clone → parse → SBOM → Codebreaker → Autopsy → cleanup."""
    tracker = ProgressTracker()
    cloned_path: Path | None = None
    stripped = repo_input.strip()
    mesh_events: list[dict[str, Any]] = []

    def capture(stage: str, message: str, status: str = "active") -> None:
        evt = tracker.event(stage, message, status=status)  # type: ignore[arg-type]
        evt["ui_status"] = tracker.ui_scan_status(stage, status)  # type: ignore[arg-type]
        mesh_events.append(evt)

    def emit(stage: str, message: str, *, status: str = "active", **extra: Any) -> dict[str, Any]:
        evt = tracker.event(stage, message, status=status, **extra)  # type: ignore[arg-type]
        evt["ui_status"] = tracker.ui_scan_status(stage, status, extra.get("result"))  # type: ignore[arg-type]
        return evt

    try:
        if GitHubHandler.is_github_url(stripped):
            yield emit("CLONING", f"🛰️ Detecting Source: {stripped}")
            yield emit("CLONING", "📥 Cloning Repository: Depth 1 clone started...")
            handler = GitHubHandler(PROJECT_ROOT)
            try:
                cloned_path = handler.clone_repository(stripped)
            except GitHubCloneError as exc:
                yield emit("CLONING", str(exc), status="error")
                return
            yield tracker.complete_stage("CLONING", "✅ Ingestion Complete: Repository cloned.")
            scan_path = str(cloned_path)
        elif stripped.lower().startswith(("http://", "https://")):
            yield emit("CLONING", "Invalid GitHub URL.", status="error")
            return
        else:
            local = Path(stripped)
            if not local.is_dir():
                yield emit("PARSING", f"Repository path does not exist: {stripped}", status="error")
                return
            scan_path = str(local.resolve())
            yield tracker.complete_stage("CLONING", "Local source detected — skipping clone.")

        from backend.scan_status import scan_status_store

        result = run_mesh_scan(
            scan_path,
            llm_config,
            scan_id=tracker.scan_id,
            status_store=scan_status_store,
            on_progress=capture,
        )

        for evt in mesh_events:
            yield evt

        try:
            advisory = ReportEngine().save_sentinel_advisory(result)
            result["advisory_file"] = str(advisory)
        except Exception:
            result["advisory_file"] = ""

        if cloned_path:
            yield emit("CLEANUP", "🧹 Cleanup Started: Purging temporary workspace...")
            GitHubHandler.cleanup(cloned_path)
            cloned_path = None
            yield tracker.complete_stage("CLEANUP", "Temporary workspace purged.")

        threats = len(result.get("findings", [])) + len(result.get("sbom_risks", []))
        outcome = "breach" if threats > 0 else "secure"
        final = tracker.complete_stage(
            "COMPLETE",
            "Scan complete." if threats else "Scan complete — perimeter secure.",
            result=result,
            outcome=outcome,
        )
        final["ui_status"] = outcome
        yield final

    except Exception as exc:
        yield tracker.error("COMPLETE", str(exc))
    finally:
        if cloned_path:
            GitHubHandler.cleanup(cloned_path)
