"""Agent mesh — Codebreaker + Autopsy feedback loop."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from agents.autopsy import audit_diagnostics
from agents.codebreaker import analyze_source_code, prefetch_memory
from backend.config.llm_config import LLMConfig
from core.memory import VectorMemory
from core.observability import TraceLogger

MAX_MESH_RETRIES = 1


class MeshState(TypedDict, total=False):
    scan_id: str
    repo_path: str
    chunks: list[dict[str, Any]]
    findings: list[dict[str, str]]
    initial_findings: list[dict[str, str]]
    llm_config: LLMConfig
    trace_logger: TraceLogger
    vector_memory: VectorMemory
    memory_context: str
    correction_prompt: str | None
    audit_status: str
    audit_feedback: str
    audit_reasoning: str
    retry_count: int
    seed_test_false_positive: bool
    memory_stored: bool
    memory_id: str
    self_correction_triggered: bool


def _route_after_audit(state: MeshState) -> Literal["analyze_source_code", "finalize_scan"]:
    if state.get("audit_status") == "retry" and state.get("retry_count", 0) <= MAX_MESH_RETRIES:
        return "analyze_source_code"
    return "finalize_scan"


def _finalize_scan(state: MeshState) -> MeshState:
    """Store correction memory and persist reasoning traces."""
    trace = state["trace_logger"]
    memory: VectorMemory = state["vector_memory"]
    memory_stored = state.get("memory_stored", False)
    memory_id = state.get("memory_id", "")

    if state.get("self_correction_triggered") and state.get("audit_feedback"):
        initial = state.get("initial_findings", [])
        final = state.get("findings", [])
        vulnerability = json.dumps(initial[:3], indent=2)
        corrected_logic = (
            f"Auditor feedback: {state.get('audit_feedback', '')}\n"
            f"Final findings: {json.dumps(final[:3], indent=2)}"
        )
        memory_id = memory.store_correction(
            vulnerability=vulnerability,
            corrected_logic=corrected_logic,
            metadata={
                "scan_id": state["scan_id"],
                "repo_path": state["repo_path"],
                "retry_count": state.get("retry_count", 0),
            },
        )
        memory_stored = True
        trace.log_event(
            "memory_stored",
            {"memory_id": memory_id, "correction": corrected_logic[:500]},
        )

    trace.log_event(
        "scan_complete",
        {
            "retry_count": state.get("retry_count", 0),
            "audit_status": state.get("audit_status", ""),
            "audit_rationale": state.get("audit_reasoning", ""),
            "findings_count": len(state.get("findings", [])),
        },
    )
    trace.save()
    return {**state, "memory_stored": memory_stored, "memory_id": memory_id}


def build_agent_mesh() -> Any:
    """Build: prefetch -> Codebreaker -> Autopsy -> (retry Codebreaker) -> finalize."""
    mesh = StateGraph(MeshState)
    mesh.add_node("prefetch_memory", prefetch_memory)
    mesh.add_node("analyze_source_code", analyze_source_code)
    mesh.add_node("audit_diagnostics", audit_diagnostics)
    mesh.add_node("finalize_scan", _finalize_scan)

    mesh.set_entry_point("prefetch_memory")
    mesh.add_edge("prefetch_memory", "analyze_source_code")
    mesh.add_edge("analyze_source_code", "audit_diagnostics")
    mesh.add_conditional_edges("audit_diagnostics", _route_after_audit)
    mesh.add_edge("finalize_scan", END)
    return mesh.compile()


def _save_scan_results(
    scan_id: str,
    repo_path: str,
    findings: list[dict[str, str]],
    files_scanned: int,
    *,
    audit_status: str,
    retry_count: int,
    memory_stored: bool,
    trace_file: str,
) -> Path:
    scans_dir = Path(__file__).resolve().parents[1] / "logs" / "scans"
    scans_dir.mkdir(parents=True, exist_ok=True)
    out_path = scans_dir / f"{scan_id}.json"
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scan_id": scan_id,
        "repo_path": repo_path,
        "files_scanned": files_scanned,
        "findings": findings,
        "audit_status": audit_status,
        "retry_count": retry_count,
        "memory_stored": memory_stored,
        "trace_file": trace_file,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def run_mesh_scan(
    repo_path: str,
    llm_config: LLMConfig,
    *,
    seed_test_false_positive: bool = False,
) -> dict[str, Any]:
    """Execute full agent mesh scan with Autopsy guardrails."""
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    from core.repo_reader import RepositoryReader

    reader = RepositoryReader(root)
    files = reader.discover_files()
    chunks = reader.chunk_for_llm()
    chunk_payloads = [
        {"file_paths": c.file_paths, "content": c.content, "byte_size": c.byte_size}
        for c in chunks
    ]

    scan_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trace_logger = TraceLogger(scan_id)
    vector_memory = VectorMemory()
    vector_memory.ensure_standard_practices()

    if not chunk_payloads:
        trace_logger.save()
        scan_file = _save_scan_results(
            scan_id,
            str(root),
            [],
            0,
            audit_status="approved",
            retry_count=0,
            memory_stored=False,
            trace_file=str(trace_logger.path),
        )
        return {
            "scan_id": scan_id,
            "repo_path": str(root),
            "files_scanned": 0,
            "findings": [],
            "scan_file": str(scan_file),
            "audit_status": "approved",
            "retry_count": 0,
            "memory_stored": False,
            "trace_file": str(trace_logger.path),
            "initial_findings": [],
            "self_correction_triggered": False,
        }

    graph = build_agent_mesh()
    result = graph.invoke(
        {
            "scan_id": scan_id,
            "repo_path": str(root),
            "chunks": chunk_payloads,
            "findings": [],
            "initial_findings": [],
            "llm_config": llm_config,
            "trace_logger": trace_logger,
            "vector_memory": vector_memory,
            "memory_context": "",
            "correction_prompt": None,
            "audit_status": "pending",
            "audit_feedback": "",
            "audit_reasoning": "",
            "retry_count": 0,
            "seed_test_false_positive": seed_test_false_positive,
            "memory_stored": False,
            "self_correction_triggered": False,
        }
    )

    findings = result.get("findings", [])
    scan_file = _save_scan_results(
        scan_id,
        str(root),
        findings,
        len(files),
        audit_status=result.get("audit_status", "approved"),
        retry_count=result.get("retry_count", 0),
        memory_stored=result.get("memory_stored", False),
        trace_file=str(trace_logger.path),
    )

    return {
        "scan_id": scan_id,
        "repo_path": str(root),
        "files_scanned": len(files),
        "findings": findings,
        "scan_file": str(scan_file),
        "audit_status": result.get("audit_status", "approved"),
        "retry_count": result.get("retry_count", 0),
        "memory_stored": result.get("memory_stored", False),
        "memory_id": result.get("memory_id", ""),
        "trace_file": str(trace_logger.path),
        "initial_findings": result.get("initial_findings", []),
        "self_correction_triggered": result.get("self_correction_triggered", False),
        "audit_feedback": result.get("audit_feedback", ""),
    }
