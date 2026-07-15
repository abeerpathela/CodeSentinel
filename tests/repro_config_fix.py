"""
Regression test — LLMConfig resolves API keys at build time (JIT), not at __init__.

Usage:
    python tests/repro_config_fix.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.config.llm_config import LLMConfig


def main() -> None:
    original = os.environ.get("GROQ_API_KEY")
    try:
        os.environ.pop("GROQ_API_KEY", None)

        config = LLMConfig()

        try:
            config._build_groq()
            print("[FAIL] Expected ValueError when GROQ_API_KEY is missing.", file=sys.stderr)
            sys.exit(1)
        except ValueError as exc:
            if "GROQ_API_KEY is not set" not in str(exc):
                print(f"[FAIL] Unexpected error message: {exc}", file=sys.stderr)
                sys.exit(1)
            print("[OK] _build_groq() raises ValueError when key is absent")

        os.environ["GROQ_API_KEY"] = "mock_key_for_jit_test"

        try:
            llm = config._build_groq()
        except ValueError as exc:
            print(f"[FAIL] Same instance failed after key was set: {exc}", file=sys.stderr)
            sys.exit(1)

        resolved = getattr(llm, "groq_api_key", None) or getattr(llm, "api_key", None)
        if not resolved:
            print("[FAIL] Built Groq client has no resolved API key attribute.", file=sys.stderr)
            sys.exit(1)
        if resolved == "":
            print("[FAIL] Resolved API key is empty string.", file=sys.stderr)
            sys.exit(1)

        print("[OK] Same LLMConfig instance resolves key dynamically after env is set")
        print("repro_config_fix passed")
    finally:
        if original is not None:
            os.environ["GROQ_API_KEY"] = original
        else:
            os.environ.pop("GROQ_API_KEY", None)


if __name__ == "__main__":
    main()
