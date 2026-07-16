"""
Phase 1 validation — verifies Groq and Gemini switchboard connectivity.

Usage:
    python tests/validate_p1.py

Requires GROQ_API_KEY and GEMINI_API_KEY in environment or .env at project root.
Stops after 3 total API failures and logs error codes.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

MAX_FAILURES = 3
LOG_DIR = ROOT / "logs"


def _log_error(code: str, message: str, provider: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": 1,
        "error_code": code,
        "provider": provider,
        "message": message,
    }
    log_path = LOG_DIR / "phase1_errors.jsonl"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    print(f"[ERROR {code}] {provider}: {message}", file=sys.stderr)


def _classify_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "api_key" in text or "authentication" in text or "401" in text:
        return "AUTH_FAILED"
    if "429" in text or "rate" in text or "resource_exhausted" in text:
        return "RATE_LIMIT"
    if "404" in text or "not_found" in text or "not found" in text:
        return "NOT_FOUND"
    if "timeout" in text or "timed out" in text:
        return "TIMEOUT"
    if "connection" in text or "network" in text:
        return "NETWORK_ERROR"
    return "API_ERROR"


def validate() -> str:
    from backend.llm_config import LLMConfig, LLMProvider

    failures = 0
    results: dict[str, str] = {}

    if not os.getenv("GROQ_API_KEY"):
        _log_error("MISSING_KEY", "GROQ_API_KEY not set", "groq")
        failures += 1
    if not os.getenv("GEMINI_API_KEY"):
        _log_error("MISSING_KEY", "GEMINI_API_KEY not set", "gemini")
        failures += 1

    if failures >= MAX_FAILURES:
        print(
            f"Validation aborted: {failures} failures (limit {MAX_FAILURES})",
            file=sys.stderr,
        )
        sys.exit(1)

    config = LLMConfig()
    key_by_provider = {
        LLMProvider.GROQ: bool(os.getenv("GROQ_API_KEY")),
        LLMProvider.GEMINI: bool(os.getenv("GEMINI_API_KEY")),
    }

    for i, provider in enumerate((LLMProvider.GROQ, LLMProvider.GEMINI)):
        if failures >= MAX_FAILURES:
            break
        if not key_by_provider[provider]:
            continue
        if i > 0:
            time.sleep(2)  # avoid RPS burst between provider calls
        try:
            reply = config.invoke(
                "Reply with exactly one word: READY",
                provider=provider,
            )
            results[provider.value] = reply.strip()
            print(f"[OK] {provider.value}: {reply.strip()[:80]}")
        except Exception as exc:
            code = _classify_error(exc)
            _log_error(code, str(exc), provider.value)
            failures += 1
            print(
                f"[FAIL] {provider.value} ({code}): {exc}",
                file=sys.stderr,
            )

    if failures >= MAX_FAILURES:
        print(
            f"\nValidation stopped: {failures} API failures (limit {MAX_FAILURES}). "
            f"See logs/phase1_errors.jsonl",
            file=sys.stderr,
        )
        sys.exit(1)

    if len(results) < 2:
        print(
            f"\nValidation incomplete: only {len(results)}/2 providers responded.",
            file=sys.stderr,
        )
        sys.exit(1)

    return "CodeSentinel Ready"


if __name__ == "__main__":
    message = validate()
    print(message)
    sys.exit(0)
