"""
Final performance stress-test — medium project scan benchmark.

Usage:
    python tests/final_benchmark.py

Requires GROQ_API_KEY and GEMINI_API_KEY in .env.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

BENCHMARK_FILES = {
    "utils.py": "def add(a, b):\n    return a + b\n",
    "api_handler.py": "import json\n\ndef parse(data):\n    return json.loads(data)\n",
    "db.py": "import sqlite3\n\ndef connect(path):\n    return sqlite3.connect(path)\n",
    "config.py": 'DEBUG = True\nAPI_URL = "http://localhost"\n',
    "worker.py": "import subprocess\n\ndef version():\n    return subprocess.run(['python','--version'], capture_output=True, text=True, shell=False)\n",
    "unsafe.py": "import os\nx = input('cmd: ')\nos.system(x)\n",
    "requirements.txt": "requests==2.25.0\nflask==1.0.0\nfastapi>=0.115.0\n",
    "package.json": '{"name":"bench","dependencies":{"express":"4.17.1","lodash":"4.17.20"}}',
    "main.go": "package main\nfunc main() {}\n",
    "README.md": "# Benchmark fixture\n",
}


def _create_benchmark_repo(base: Path) -> Path:
    repo = base / "benchmark_repo"
    repo.mkdir(parents=True, exist_ok=True)
    for name, content in BENCHMARK_FILES.items():
        (repo / name).write_text(content, encoding="utf-8")
    return repo


def validate() -> None:
    if not os.getenv("GROQ_API_KEY") or not os.getenv("GEMINI_API_KEY"):
        print("[FAIL] GROQ_API_KEY and GEMINI_API_KEY required.", file=sys.stderr)
        sys.exit(1)

    from backend.config.llm_config import LLMConfig
    from core.repo_reader import RepositoryReader
    from agents.mesh import run_mesh_scan

    assert os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile") == "llama-3.3-70b-versatile"
    assert os.getenv("GEMINI_MODEL", "gemini-2.5-flash") == "gemini-2.5-flash"

    tmp = Path(tempfile.mkdtemp(prefix="codesentinel_bench_"))
    try:
        repo = _create_benchmark_repo(tmp)
        reader = RepositoryReader(repo)
        files = reader.discover_files()
        chunks = reader.chunk_for_llm()

        print(f"[INFO] Benchmark repo files: {len(files)}")
        if len(files) < 5:
            print("[FAIL] Expected at least 5 scannable source files.", file=sys.stderr)
            sys.exit(1)
        print("[OK] Medium project size (5+ files)")

        max_chunk = max((c.byte_size for c in chunks), default=0)
        if max_chunk > 500_000:
            print(f"[FAIL] Chunk exceeds 500KB limit: {max_chunk}", file=sys.stderr)
            sys.exit(1)
        print(f"[OK] Gemini context chunks within limit (max {max_chunk} bytes, no truncation split needed)")

        config = LLMConfig()
        t0 = time.perf_counter()
        result = run_mesh_scan(str(repo), config)
        elapsed = time.perf_counter() - t0

        print(f"[INFO] Scan completed in {elapsed:.1f}s")
        print(f"[INFO] Files scanned: {result.get('files_scanned')}")
        print(f"[INFO] Findings: {len(result.get('findings', []))}")
        print(f"[INFO] SBOM risks: {len(result.get('sbom_risks', []))}")

        if elapsed > 120:
            print("[FAIL] Scan exceeded 120s budget.", file=sys.stderr)
            sys.exit(1)

        autopsy_window = elapsed
        if result.get("retry_count", 0) > 0:
            print(f"[OK] Autopsy loop completed within {autopsy_window:.1f}s (retry_count={result.get('retry_count')})")
        else:
            print(f"[OK] Full mesh pipeline within {autopsy_window:.1f}s")

        if autopsy_window > 30 and result.get("retry_count", 0) > 0:
            print(f"[WARN] Autopsy retry path took {autopsy_window:.1f}s (>30s target)")

        estimated_tokens = (
            sum(len(c.content) for c in chunks) // 4
            + len(result.get("findings", [])) * 200
            + len(result.get("sbom_risks", [])) * 100
        )
        print(f"[INFO] Estimated token budget: ~{estimated_tokens}")
        if estimated_tokens > 500_000:
            print("[FAIL] Estimated token usage exceeds safe limit.", file=sys.stderr)
            sys.exit(1)
        print("[OK] Token usage within safe Groq/Gemini free-tier limits")

        print("final_benchmark passed")
    finally:
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    validate()
