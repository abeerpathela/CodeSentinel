"""Codebreaker agent — LangGraph node for offensive-defensive source inspection."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from backend.config.llm_config import LLMConfig, _extract_content
from core.repo_reader import FileChunk, RepositoryReader

SYSTEM_PROMPT = """You are an Offensive-Defensive AI security analyst for supply chain defense.

Analyze the provided source code chunk and identify security issues in these categories:
1. Hardcoded credentials (API keys, passwords, tokens, secrets in source)
2. Remote command execution (os.system, subprocess with shell=True, unsanitized exec/eval)
3. Supply chain anomalies (suspicious import names, typosquatting, obfuscated dependencies)
4. Backdoors or logic bombs (hidden triggers, time bombs, unauthorized remote access)

Return ONLY a JSON array. Each element must have exactly these keys:
- file_path (string, relative path from the --- FILE: header)
- vulnerability_type (string, e.g. "Hardcoded Credential", "Remote Command Execution")
- severity (string: "High", "Medium", or "Low")
- description (string, concise explanation)

If no issues are found, return an empty array: []
Do not wrap the JSON in markdown fences."""


class CodebreakerState(TypedDict):
    repo_path: str
    chunks: list[dict[str, Any]]
    findings: list[dict[str, str]]
    llm_config: LLMConfig


def _parse_findings(raw: str) -> list[dict[str, str]]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []

    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    findings: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        finding = {
            "file_path": str(item.get("file_path", "unknown")),
            "vulnerability_type": str(item.get("vulnerability_type", "Unknown")),
            "severity": str(item.get("severity", "Low")),
            "description": str(item.get("description", "")),
        }
        findings.append(finding)
    return findings


def analyze_source_code(state: CodebreakerState) -> CodebreakerState:
    """LangGraph node: send each chunk to Gemini (large context) for security analysis."""
    llm = state["llm_config"].get_llm(large_context=True)
    all_findings: list[dict[str, str]] = list(state.get("findings", []))

    for chunk_data in state["chunks"]:
        file_list = ", ".join(chunk_data["file_paths"])
        user_prompt = (
            f"Repository: {state['repo_path']}\n"
            f"Files in this chunk: {file_list}\n\n"
            f"{chunk_data['content']}"
        )

        response = llm.invoke(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
        text = _extract_content(response)
        all_findings.extend(_parse_findings(text))

    return {**state, "findings": all_findings}


def build_codebreaker_graph() -> Any:
    """Build a single-node LangGraph pipeline for source analysis."""
    graph = StateGraph(CodebreakerState)
    graph.add_node("analyze_source_code", analyze_source_code)
    graph.set_entry_point("analyze_source_code")
    graph.add_edge("analyze_source_code", END)
    return graph.compile()


def _save_scan_results(repo_path: str, findings: list[dict[str, str]], files_scanned: int) -> Path:
    scans_dir = Path(__file__).resolve().parents[1] / "logs" / "scans"
    scans_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = scans_dir / f"{timestamp}.json"
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo_path": repo_path,
        "files_scanned": files_scanned,
        "findings": findings,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def run_scan(repo_path: str, llm_config: LLMConfig) -> dict[str, Any]:
    """Execute a full Codebreaker scan on a local repository path."""
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    reader = RepositoryReader(root)
    files = reader.discover_files()
    chunks: list[FileChunk] = reader.chunk_for_llm()

    chunk_payloads = [
        {"file_paths": c.file_paths, "content": c.content, "byte_size": c.byte_size}
        for c in chunks
    ]

    if not chunk_payloads:
        findings: list[dict[str, str]] = []
        scan_file = _save_scan_results(str(root), findings, 0)
        return {
            "scan_id": scan_file.stem,
            "repo_path": str(root),
            "files_scanned": 0,
            "findings": findings,
            "scan_file": str(scan_file),
        }

    graph = build_codebreaker_graph()
    result = graph.invoke(
        {
            "repo_path": str(root),
            "chunks": chunk_payloads,
            "findings": [],
            "llm_config": llm_config,
        }
    )

    findings = result.get("findings", [])
    scan_file = _save_scan_results(str(root), findings, len(files))

    return {
        "scan_id": scan_file.stem,
        "repo_path": str(root),
        "files_scanned": len(files),
        "findings": findings,
        "scan_file": str(scan_file),
    }
