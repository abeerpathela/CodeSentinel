"""Codebreaker agent — LangGraph node for offensive-defensive source inspection."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.llm_config import LLMConfig, _extract_content
from core.observability import TraceLogger

SYSTEM_PROMPT = """You are an Offensive-Defensive AI security analyst for supply chain defense.

Analyze the provided source code chunk and identify security issues in these categories:
1. Hardcoded credentials (API keys, passwords, tokens, secrets in source)
2. Remote Command Execution (RCE) — see strict definition below
3. Supply chain anomalies (suspicious import names, typosquatting, obfuscated dependencies)
4. Backdoors or logic bombs (hidden triggers, time bombs, unauthorized remote access)

CRITICAL — Process Execution ≠ Remote Command Execution (RCE):
- SAFE (do NOT flag): subprocess.run(["fixed", "args"], shell=False), subprocess.call with
  literal argument lists, fixed executable paths, and NO untrusted/external input.
- RCE ONLY applies when untrusted data (user input, environment variables, network/request
  data, file uploads, CLI args) influences the command string, executable path, or arguments.
- Examples of RCE: os.system(user_input), subprocess.run(cmd, shell=True) where cmd is tainted,
  subprocess.run([exe, user_data]) where exe or user_data comes from untrusted sources.

Return ONLY a JSON array. Each element must have exactly these keys:
- file_path (string, relative path from the --- FILE: header)
- vulnerability_type (string, e.g. "Hardcoded Credential", "Remote Command Execution")
- severity (string: "High", "Medium", or "Low")
- description (string, concise explanation citing untrusted data flow when claiming RCE)

If no issues are found, return an empty array: []
Do not wrap the JSON in markdown fences."""

TEST_FALSE_POSITIVE = {
    "file_path": "safe_subprocess.py",
    "vulnerability_type": "Remote Command Execution",
    "severity": "High",
    "description": "Uses subprocess.run which executes remote commands.",
}


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
        findings.append(
            {
                "file_path": str(item.get("file_path", "unknown")),
                "vulnerability_type": str(item.get("vulnerability_type", "Unknown")),
                "severity": str(item.get("severity", "Low")),
                "description": str(item.get("description", "")),
            }
        )
    return findings


def prefetch_memory(state: dict[str, Any]) -> dict[str, Any]:
    """Pre-fetch past mistakes from ChromaDB before Codebreaker analysis."""
    memory = state["vector_memory"]
    query = f"security scan {state['repo_path']}"
    context = memory.query_past_mistakes(query)
    trace: TraceLogger = state["trace_logger"]
    trace.log_event("memory_prefetch", {"context_length": len(context), "memory_count": memory.count()})
    return {**state, "memory_context": context}


def analyze_source_code(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: send each chunk to Gemini (large context) for security analysis."""
    llm_config: LLMConfig = state["llm_config"]
    trace: TraceLogger = state["trace_logger"]
    llm = llm_config.get_llm(large_context=True)
    model = llm_config.GEMINI_MODEL

    retry_count = state.get("retry_count", 0)
    is_first_pass = retry_count == 0 and not state.get("correction_prompt")

    if is_first_pass and not state.get("initial_findings"):
        state = {**state, "initial_findings": []}

    system_parts = [SYSTEM_PROMPT]
    memory_context = state.get("memory_context", "")
    if memory_context:
        system_parts.append(f"\n{memory_context}")
    correction = state.get("correction_prompt")
    if correction:
        system_parts.append(f"\n{correction}")
    system_content = "\n".join(system_parts)

    all_findings: list[dict[str, str]] = []

    for chunk_data in state["chunks"]:
        file_list = ", ".join(chunk_data["file_paths"])
        user_prompt = (
            f"Repository: {state['repo_path']}\n"
            f"Files in this chunk: {file_list}\n\n"
            f"{chunk_data['content']}"
        )
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ]

        response = llm.invoke(messages)
        text = _extract_content(response)
        chunk_findings = _parse_findings(text)
        all_findings.extend(chunk_findings)

        trace.log_llm_call(
            agent="codebreaker",
            model=model,
            llm_input=messages,
            llm_output=text,
            reasoning_path=f"Analyzed chunk [{file_list}] — {len(chunk_findings)} finding(s).",
            metadata={"retry_count": retry_count, "chunk_files": chunk_data["file_paths"]},
        )

    if state.get("seed_test_false_positive") and is_first_pass:
        all_findings.append(dict(TEST_FALSE_POSITIVE))
        trace.log_event("seed_test_false_positive", {"finding": TEST_FALSE_POSITIVE})

    from agents.autopsy import _is_rce_false_positive

    chunks = state.get("chunks", [])
    if state.get("correction_prompt") or state.get("retry_count", 0) > 0:
        all_findings = [
            f for f in all_findings if not _is_rce_false_positive(f, chunks)
        ]

    updates: dict[str, Any] = {**state, "findings": all_findings}
    if is_first_pass:
        updates["initial_findings"] = list(all_findings)

    return updates
