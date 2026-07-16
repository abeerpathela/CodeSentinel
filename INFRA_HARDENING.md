# CodeSentinel — CNI Infrastructure Hardening Guide

This document describes how CodeSentinel would be deployed in a **Critical National Infrastructure (CNI)** environment such as energy grids, water treatment, transport signalling, or telecommunications backbone systems.

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CNI Operations Zone                       │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Analyst    │───▶│  API Gateway │───▶│  CodeSentinel │  │
│  │  Workstation│    │  (Rate Limit)│    │  Backend      │  │
│  └─────────────┘    └──────────────┘    └───────┬───────┘  │
│                                                  │          │
│                     Air-Gap Boundary ────────────┼────────── │
│                                                  ▼          │
│                              ┌───────────────────────────┐  │
│                              │  Local LLM Proxy / Keys   │  │
│                              │  (Groq + Gemini endpoints)│  │
│                              └───────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Air-Gapped Support

For fully air-gapped CNI deployments:

1. **Offline package mirror** — Pre-build `.venv` and `frontend/dist` on a connected staging machine; transfer via approved media.
2. **Local ChromaDB** — Vector memory (`data/chroma/`) requires no external network once seeded with standard practices.
3. **Threat intelligence** — Replace simulated `VULNERABLE_PACKAGES` in `core/sbom.py` with a local CVE feed (JSON/SQLite) updated through the approved change window.
4. **LLM endpoints** — Route Groq/Gemini calls through an organisation-approved AI gateway with audit logging. For strict air-gap, substitute with on-prem models behind the same `LLMConfig` interface.

## API Gateway Limits

Recommended production limits on `/codebreaker/scan`:

| Control | Recommendation |
|---------|----------------|
| Rate limit | 5 scans / hour / analyst |
| Concurrent scans | Max 2 parallel mesh invocations |
| Request body size | 1 KB (repo path only) |
| Response timeout | 180 seconds |
| Authentication | mTLS or OAuth2 bearer tokens |

Implement at the reverse proxy (nginx, Traefik, or Azure API Management) in front of uvicorn.

## Data Classification

| Asset | Classification | Retention |
|-------|---------------|-----------|
| `logs/scans/` | CONFIDENTIAL | 90 days, auto-prune to 10 |
| `logs/traces/` | CONFIDENTIAL | 90 days |
| `logs/reports/` | OFFICIAL-SENSITIVE | 1 year |
| `data/chroma/` | INTERNAL | Indefinite (corrections only) |
| `.env` | SECRET | Never commit; HSM-backed in prod |

## Hardening Checklist

- [ ] Run backend as non-root service account
- [ ] Disable `--reload` in production uvicorn
- [ ] Serve frontend as static `dist/` via HTTPS only
- [ ] Enable CORS allowlist to analyst subnet only
- [ ] Rotate `GROQ_API_KEY` and `GEMINI_API_KEY` quarterly
- [ ] Export audit reports to SIEM via `/analytics/export`
- [ ] Run `tests/gauntlet.py` after every deployment

## Incident Response Integration

1. **Detection** — Codebreaker flags threat in scan JSON
2. **Validation** — Autopsy suppresses false positives before alert
3. **Reporting** — `ReportEngine` generates Markdown audit trail
4. **Escalation** — Forward report to SOC via approved channel

## Contact

For CNI deployment support, maintain an internal runbook referencing `run_sentinel.ps1` and this document.
