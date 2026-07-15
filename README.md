# CodeSentinel

**Agentic Supply Chain Defense** — a dual-LLM security platform that scans local repositories for vulnerabilities, audits findings with self-correction, and maps supply-chain risk through SBOM analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Sentinel Dashboard (React)                  │
│         Scan Engine · Threat Heatmap · Autopsy Feed           │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + polling
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend (Python)                    │
│  /codebreaker/scan · /analytics/summary · /analytics/resilience│
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  Codebreaker          Autopsy            SBOM Parser
  (Gemini 2.5)         (Groq Llama 3.3)   (Groq + threat intel)
        │                  │                  │
        └──────── LangGraph Mesh ────────────┘
                           │
              ChromaDB Memory · Trace Logs · Scan History
```

### Agent Mesh Pipeline

1. **Prefetch** — load past mistakes from ChromaDB vector memory
2. **Codebreaker** (Gemini `gemini-2.5-flash`) — large-context source analysis
3. **Autopsy** (Groq `llama-3.3-70b-versatile`) — auditor rejects false positives
4. **Retry loop** — max 1 correction pass with inline prompt injection
5. **SBOM** — parse `requirements.txt` / `package.json` / `go.mod` for transitive risks

## Why Groq + Gemini?

| Provider | Model | Role | Rationale |
|----------|-------|------|-----------|
| **Google Gemini** | `gemini-2.5-flash` | Codebreaker (scanner) | Large context window (~500KB chunks) for whole-file and multi-file analysis |
| **Groq** | `llama-3.3-70b-versatile` | Autopsy (auditor) | Fast, low-latency reasoning for false-positive detection and SBOM enrichment |

Gemini handles **breadth** (reading lots of code). Groq handles **speed + judgment** (auditing and correcting). Together they form a cost-efficient dual-LLM mesh without relying on a single provider.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- API keys: [Groq](https://console.groq.com/keys) and [Google AI Studio](https://aistudio.google.com/apikey)

### 1. Environment Setup

```powershell
cd CodeSentinel
copy .env.example .env
# Edit .env with your API keys

.\setup_env.ps1
```

### 2. One-Click Launch

```powershell
.\run_sentinel.ps1
```

| Service | URL |
|---------|-----|
| Dashboard | http://127.0.0.1:5173 |
| API Docs | http://127.0.0.1:8000/docs |
| Resilience | http://127.0.0.1:8000/analytics/resilience |

### 3. Manual Launch

```powershell
# Terminal 1 — Backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

## Validation Suite

```powershell
.\.venv\Scripts\python.exe tests\validate_p1.py      # LLM connectivity
.\.venv\Scripts\python.exe tests\validate_p3.py      # Autopsy self-correction
.\.venv\Scripts\python.exe tests\final_benchmark.py  # Performance stress-test
```

## Project Structure

```
CodeSentinel/
├── agents/          # LangGraph mesh (codebreaker, autopsy)
├── backend/         # FastAPI + analytics + scan status
├── core/            # repo_reader, sbom, memory, observability
├── frontend/        # React dashboard (Vite + Tailwind)
├── tests/           # Validation scripts (p1–p4, benchmark)
├── logs/            # Scans, traces (auto-pruned to last 10)
├── data/chroma/     # Vector memory (gitignored)
├── run_sentinel.ps1 # 1-click launcher
└── setup_env.ps1    # Python venv bootstrap
```

## License

MIT — built as a Phase 1–4 MVP for agentic supply chain defense.
