"""Autopsy agent — Groq auditor that validates Codebreaker diagnostics."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.config.llm_config import LLMConfig, _extract_content
from core.observability import TraceLogger

AUDITOR_SYSTEM_PROMPT = """You are a Senior Security Auditor reviewing Codebreaker findings.

STRICT AUDIT CRITERIA — apply to EVERY finding regardless of severity (High, Medium, or Low):

1. Attacker Control (required for Remote Command Execution / RCE):
   - RCE is valid ONLY if untrusted data (user input, env vars, network/request data, file uploads)
     influences the command string, executable path, or argument list.
   - Process Execution ≠ RCE. subprocess.run(["fixed", "args"], shell=False) with literal arguments
     and no untrusted input is SAFE — reject any RCE finding on such code.

2. Evidence requirement:
   - Each finding must cite a concrete untrusted-data source or dangerous pattern.
   - Reject vague reasoning or severity inflation.

3. False positives to reject immediately:
   - RCE on safe_subprocess.py-style fixed-argument subprocess.run(..., shell=False)
   - RCE on os.path.join, json.loads, or other standard library helpers
   - Findings with no untrusted data flow described

Return ONLY JSON with this exact shape:
{
  "approved": true or false,
  "audit_rationale": "Concise evidence list used to approve/reject each finding",
  "feedback": "Correction guidance for the analyzer if not approved",
  "false_positives": ["file_path entries that are false positives"],
  "weak_findings": ["file_path entries with weak reasoning or missing attacker control"]
}

Set approved to false if ANY finding is an obvious false positive or lacks attacker control evidence.
Do not approve RCE findings unless untrusted input flow is identified."""


def _file_content(file_path: str, chunks: list[dict[str, Any]]) -> str:
    target = file_path.replace("\\", "/").lower()
    for chunk in chunks:
        for fp in chunk.get("file_paths", []):
            if fp.replace("\\", "/").lower() == target or target in fp.replace("\\", "/").lower():
                return chunk.get("content", "")
        content = chunk.get("content", "")
        marker = f"--- FILE: {file_path}"
        if marker in content:
            return content
    return ""


def _has_untrusted_input_flow(source: str) -> bool:
    untrusted_patterns = (
        "input(",
        "os.environ",
        "environ[",
        "sys.argv",
        "request.",
        "req.",
        "socket.recv",
        "stdin",
        "input()",
        "eval(",
        "exec(",
        "pickle.loads",
        "yaml.load(",
    )
    source_lower = source.lower()
    return any(p.lower() in source_lower for p in untrusted_patterns)


def _is_safe_fixed_subprocess(source: str) -> bool:
    normalized = source.replace(" ", "")
    if "subprocess.run([" not in normalized and "subprocess.call([" not in normalized:
        return False
    if "shell=True" in normalized:
        return False
    if "shell=False" not in normalized:
        return False
    return not _has_untrusted_input_flow(source)


def _is_rce_false_positive(finding: dict[str, str], chunks: list[dict[str, Any]]) -> bool:
    vtype = finding.get("vulnerability_type", "").lower()
    if "remote command" not in vtype and "rce" not in vtype and "command execution" not in vtype:
        return False

    source = _file_content(finding.get("file_path", ""), chunks)
    if not source:
        return False

    if _is_safe_fixed_subprocess(source):
        return True

    if "subprocess" in source.lower() and not _has_untrusted_input_flow(source):
        if "shell=True" not in source.replace(" ", "") and "os.system" not in source:
            return True
    return False


def _programmatic_audit(
    findings: list[dict[str, str]], chunks: list[dict[str, Any]]
) -> dict[str, Any] | None:
    false_positives = [
        f.get("file_path", "")
        for f in findings
        if _is_rce_false_positive(f, chunks)
    ]
    if not false_positives:
        return None

    rationale_parts = [
        f"Rejected RCE on {fp}: no untrusted input flow; static subprocess with shell=False is safe."
        for fp in false_positives
    ]
    return {
        "approved": False,
        "audit_rationale": " | ".join(rationale_parts),
        "feedback": (
            "Remove RCE findings on fixed-argument subprocess.run(..., shell=False). "
            "RCE requires untrusted input influencing command, path, or arguments."
        ),
        "false_positives": false_positives,
        "weak_findings": false_positives,
    }


def _parse_audit_response(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return {
            "approved": False,
            "audit_rationale": "Unable to parse auditor response",
            "feedback": "Re-analyze with evidence-backed findings only.",
            "false_positives": [],
            "weak_findings": [],
        }

    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {
            "approved": False,
            "audit_rationale": "Invalid JSON from auditor",
            "feedback": "Return strictly valid JSON findings with clear evidence.",
            "false_positives": [],
            "weak_findings": [],
        }

    rationale = str(data.get("audit_rationale", data.get("reasoning_path", "")))
    return {
        "approved": bool(data.get("approved", False)),
        "audit_rationale": rationale,
        "feedback": str(data.get("feedback", "")),
        "false_positives": list(data.get("false_positives", [])),
        "weak_findings": list(data.get("weak_findings", [])),
    }


def _build_correction_prompt(audit: dict[str, Any]) -> str:
    fp_entries = audit.get("false_positives", [])
    lines = [
        "FALSE POSITIVE CORRECTION — Senior Auditor rejected prior findings.",
        audit.get("feedback", ""),
        f"Audit rationale: {audit.get('audit_rationale', '')}",
    ]
    for fp in fp_entries:
        lines.append(
            f"The auditor rejected finding on '{fp}' because it lacks untrusted data flow. "
            "Re-analyze and remove false positives."
        )
    if not fp_entries:
        lines.append(
            "Re-analyze and remove findings that lack attacker control / untrusted input flow."
        )
    lines.append(
        "Remember: Process Execution ≠ RCE. "
        "subprocess.run([fixed, args], shell=False) with no untrusted input is SAFE."
    )
    lines.append("Return ONLY evidence-backed JSON findings.")
    return "\n".join(lines)


def audit_diagnostics(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: Groq auditor reviews Codebreaker findings."""
    llm_config: LLMConfig = state["llm_config"]
    trace: TraceLogger = state["trace_logger"]
    findings = state.get("findings", [])
    chunks = state.get("chunks", [])

    programmatic = _programmatic_audit(findings, chunks)

    llm = llm_config.get_llm(large_context=False)
    model = llm_config.GROQ_MODEL

    user_prompt = (
        f"Repository: {state['repo_path']}\n"
        f"Retry attempt: {state.get('retry_count', 0)}\n\n"
        f"Findings to audit ({len(findings)}):\n"
        f"{json.dumps(findings, indent=2)}\n\n"
        "Source context (for attacker-control verification):\n"
        f"{json.dumps([c.get('content', '')[:4000] for c in chunks], indent=2)}\n\n"
        "Audit EVERY finding for attacker control and false positives. Severity does not bypass audit."
    )
    messages = [
        {"role": "system", "content": AUDITOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    response = llm.invoke(messages)
    raw_output = _extract_content(response)
    audit = _parse_audit_response(raw_output)

    if programmatic and programmatic.get("false_positives"):
        audit["approved"] = False
        audit["false_positives"] = list(
            set(audit.get("false_positives", []) + programmatic["false_positives"])
        )
        audit["audit_rationale"] = (
            programmatic["audit_rationale"]
            + (" | LLM: " + audit["audit_rationale"] if audit.get("audit_rationale") else "")
        )
        if not audit.get("feedback"):
            audit["feedback"] = programmatic["feedback"]

    trace.log_llm_call(
        agent="autopsy",
        model=model,
        llm_input=messages,
        llm_output=raw_output,
        reasoning_path=audit["audit_rationale"],
        metadata={
            "approved": audit["approved"],
            "audit_rationale": audit["audit_rationale"],
            "false_positives": audit["false_positives"],
            "weak_findings": audit["weak_findings"],
            "programmatic_override": programmatic is not None,
        },
    )

    if audit["approved"]:
        trace.log_event(
            "audit_approved",
            {
                "findings_count": len(findings),
                "retry_count": state.get("retry_count", 0),
                "audit_rationale": audit["audit_rationale"],
            },
        )
        return {
            **state,
            "audit_status": "approved",
            "audit_feedback": audit["feedback"],
            "audit_reasoning": audit["audit_rationale"],
        }

    trace.log_event(
        "audit_rejected",
        {
            "feedback": audit["feedback"],
            "false_positives": audit["false_positives"],
            "weak_findings": audit["weak_findings"],
            "retry_count": state.get("retry_count", 0),
            "audit_rationale": audit["audit_rationale"],
        },
    )
    new_retry_count = state.get("retry_count", 0) + 1
    return {
        **state,
        "audit_status": "retry",
        "audit_feedback": audit["feedback"],
        "audit_reasoning": audit["audit_rationale"],
        "self_correction_triggered": True,
        "correction_prompt": _build_correction_prompt(audit),
        "retry_count": new_retry_count,
    }
