"""Deterministic static heuristics for demo fixtures and LLM fallback."""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any


def _read_py_files(root: Path) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    for path in root.rglob("*.py"):
        if any(part.startswith(".") for part in path.parts):
            continue
        try:
            files.append((str(path.relative_to(root)).replace("\\", "/"), path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return files


def static_analyze(repo_path: str | Path) -> list[dict[str, str]]:
    """Rule-based scan used when Codebreaker LLM is unavailable."""
    root = Path(repo_path).resolve()
    findings: list[dict[str, str]] = []

    for rel_path, source in _read_py_files(root):
        lower = source.lower()

        if "base64" in lower and ("exec(" in lower or "eval(" in lower):
            if re.search(r"b64decode|base64\.b64decode", source, re.I):
                findings.append(
                    {
                        "file_path": rel_path,
                        "vulnerability_type": "Logic Bomb / Backdoor",
                        "severity": "Critical",
                        "description": "Obfuscated base64 payload executed via exec/eval — time-delayed backdoor pattern.",
                    }
                )

        if "os.environ" in lower and "subprocess" in lower:
            findings.append(
                {
                    "file_path": rel_path,
                    "vulnerability_type": "Remote Command Execution (RCE)",
                    "severity": "High",
                    "description": "Untrusted environment variable flows into subprocess invocation — attacker-controlled executable path.",
                }
            )

        if "shell=true" in lower.replace(" ", ""):
            findings.append(
                {
                    "file_path": rel_path,
                    "vulnerability_type": "Remote Command Execution (RCE)",
                    "severity": "High",
                    "description": "subprocess invoked with shell=True — command injection risk.",
                }
            )

    return findings


def merge_findings(primary: list[dict[str, str]], fallback: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = {f.get("file_path", "") for f in primary}
    merged = list(primary)
    for f in fallback:
        if f.get("file_path") not in seen:
            merged.append(f)
    return merged
