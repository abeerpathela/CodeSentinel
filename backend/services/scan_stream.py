"""Generator-based scan pipeline with SSE progress yields."""

from __future__ import annotations

import shutil
from collections.abc import Generator
from pathlib import Path
from typing import Any

from agents.mesh import run_mesh_scan
from backend.llm_config import LLMConfig
from core.workspace import WorkspaceManager
from backend.services.progress_stream import ProgressTracker
from backend.services.scan_session import register_workspace
from core.github_handler import GitHubCloneError, GitHubHandler
from core.reporter import ReportEngine

IGNORE = shutil.ignore_patterns(
    ".git", "__pycache__", ".venv", "venv", "node_modules", ".chroma"
)


def _stage_local_workspace(scan_id: str, local: Path) -> Path:
    if any(WorkspaceManager.get_workspace(scan_id).iterdir()):
        WorkspaceManager.release_workspace(scan_id)
    dest = WorkspaceManager.get_workspace(scan_id)
    shutil.copytree(local, dest, ignore=IGNORE, dirs_exist_ok=True)
    return dest.resolve()


def iter_scan(repo_input: str, llm_config: LLMConfig) -> Generator[dict[str, Any], None, None]:
    """Yield progress events through clone → parse → SBOM → Codebreaker → Autopsy → retention."""
    tracker = ProgressTracker()
    scan_id = tracker.scan_id
    stripped = repo_input.strip()
    mesh_events: list[dict[str, Any]] = []
    workspace_retained = False

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
            handler = GitHubHandler()
            try:
                handler.clone_repository(stripped, scan_id)
            except GitHubCloneError as exc:
                yield emit("CLONING", str(exc), status="error")
                return
            yield tracker.complete_stage("CLONING", "✅ Ingestion Complete: Repository cloned.")
            workspace_retained = True
        elif stripped.lower().startswith(("http://", "https://")):
            yield emit("CLONING", "Invalid GitHub URL.", status="error")
            return
        else:
            local = Path(stripped)
            if not local.is_dir():
                yield emit("PARSING", f"Repository path does not exist: {stripped}", status="error")
                return
            _stage_local_workspace(scan_id, local.resolve())
            yield tracker.complete_stage("CLONING", "Local source staged to scan workspace.")
            workspace_retained = True

        scan_path = str(WorkspaceManager.get_workspace(scan_id))

        from backend.scan_status import scan_status_store

        result = run_mesh_scan(
            scan_path,
            llm_config,
            scan_id=scan_id,
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

        if workspace_retained:
            register_workspace(scan_id)
            yield emit(
                "CLEANUP",
                "Workspace retained for Ship-to-GitHub (1h TTL).",
                status="done",
            )

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
