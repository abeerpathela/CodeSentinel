# 🛡️ CodeSentinel

> **AI-Powered Agentic Supply Chain Security Platform**

CodeSentinel is a production-ready security platform that performs intelligent source code analysis, software supply chain auditing, and automated vulnerability triage using a collaborative multi-agent AI architecture.

Unlike traditional static analyzers, CodeSentinel combines multiple specialized LLM agents to detect vulnerabilities, validate findings, reduce false positives, and generate enterprise-ready security reports—all through an interactive web dashboard.

---

## 🌐 Live Demo

> **Click on the image below to visit the live website.**

<p align="center">
  <a href="https://code-sentinel-gules.vercel.app" target="_blank">
    <img src="https://github.com/user-attachments/assets/7e9f94f7-92c8-4cab-8f0f-3c2eb53f2d3c" alt="CodeSentinel Demo" width="100%">
  </a>
</p>

**Backend API**
https://codesentinel-um2c.onrender.com

**Swagger Documentation**
https://codesentinel-um2c.onrender.com/docs

---

# ✨ Features

- 🔍 Scan both **Local Projects** and **Public GitHub Repositories**
- 🤖 Multi-Agent AI Security Analysis
- 🧠 Self-Correcting Detection Pipeline
- 📦 Software Bill of Materials (SBOM) Analysis
- 🌐 Dependency Supply Chain Visualization
- 📊 Executive Security Reports
- 📈 Real-Time Scan Progress
- 🛰️ Live Agent Reasoning Terminal
- 🔐 GitHub OAuth Authentication
- ☁️ One-click "Ship to GitHub" Integration
- 📚 Persistent Scan History
- ⚡ Production Ready Deployment

---

# 🏗 Architecture

```text
                              ┌───────────────────────────────┐
                              │      React Dashboard          │
                              │  Vite • Tailwind • Framer     │
                              │ React Three Fiber • Recharts  │
                              └──────────────┬────────────────┘
                                             │
                                    REST API + SSE
                                             │
                         ┌───────────────────▼──────────────────┐
                         │       FastAPI Backend (Python)        │
                         │ Authentication • Analytics • Reports  │
                         └───────────────────┬──────────────────┘
                                             │
         ┌───────────────────────────────────┼─────────────────────────────────────┐
         │                                   │                                     │
         ▼                                   ▼                                     ▼
   Codebreaker Agent                  Autopsy Agent                      SBOM Analyzer
 (Gemini 2.5 Flash)             (Groq Llama 3.3 70B)               Dependency Intelligence
         │                                   │                                     │
         └────────────────────── LangGraph Agent Mesh ─────────────────────────────┘
                                             │
             ChromaDB Memory • Scan History • Trace Logs • Executive Reports
```

---

# 🧠 Multi-Agent Pipeline

## 1. Repository Acquisition

- Local Folder Scan
- Public GitHub Repository Clone
- Temporary Secure Workspace

---

## 2. Codebreaker Agent

**Model**

Google Gemini 2.5 Flash

Responsibilities

- Large Context Source Analysis
- Code Pattern Recognition
- Vulnerability Detection
- Secret Discovery
- Dangerous API Usage

---

## 3. Autopsy Agent

**Model**

Groq Llama 3.3 70B Versatile

Responsibilities

- Audit every finding
- Remove false positives
- Improve confidence
- Self-correct detection

---

## 4. SBOM Intelligence

Automatically analyzes

- package.json
- package-lock.json
- requirements.txt
- poetry.lock
- go.mod
- Pipfile

Features

- Dependency Graph
- Supply Chain Risks
- Version Validation
- Vulnerability Prioritization

---

## 5. Executive Report

Generates

- Threat Summary
- Severity Breakdown
- SBOM Assessment
- AI Recommendations
- Enterprise Advisory Report

---

# 🚀 Technology Stack

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- React Three Fiber
- Framer Motion
- Recharts

## Backend

- FastAPI
- Python
- LangGraph
- ChromaDB
- GitPython
- NetworkX

## AI Models

| Provider | Model | Purpose |
|-----------|-------|----------|
| Google | Gemini 2.5 Flash | Primary Security Scanner |
| Groq | Llama 3.3 70B Versatile | Security Auditor |
| LangGraph | Agent Mesh | Multi-Agent Orchestration |

---

# 🎯 Dashboard Modules

### 🛡 Triage Center

Real-time scan monitoring with live AI reasoning.

---

### 📦 Supply Chain Map

Interactive dependency graph showing package relationships and vulnerable nodes.

---

### 🧪 Security Lab

Execute Red-Team fixtures including

- Logic Bombs
- Supply Chain Attacks
- Remote Code Execution Scenarios

---

### 📑 Report Archive

Download executive audit reports generated after every completed scan.

---

# 🔐 GitHub Integration

CodeSentinel supports GitHub OAuth.

Features include

- Login using GitHub
- Scan Public Repositories
- Clone repositories securely
- Push corrected code to a new private repository
- Secure session handling

---

# 📈 Enterprise Workflow

```text
GitHub Repository
        │
        ▼
Clone Repository
        │
        ▼
Codebreaker Analysis
        │
        ▼
Autopsy Validation
        │
        ▼
SBOM Analysis
        │
        ▼
Threat Matrix
        │
        ▼
Executive Report
        │
        ▼
Push Fixed Repository to GitHub
```

---

# ⚙ Installation

## Clone

```bash
git clone https://github.com/abeerpathela/CodeSentinel.git

cd CodeSentinel
```

---

## Backend

```bash
python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt
```

---

## Frontend

```bash
cd frontend

npm install
```

---

## Environment Variables

```env
GOOGLE_API_KEY=

GROQ_API_KEY=

GITHUB_CLIENT_ID=

GITHUB_CLIENT_SECRET=

GITHUB_REDIRECT_URI=

SESSION_SECRET=

FRONTEND_URL=

VITE_API_BASE_URL=
```

---

## Run

```powershell
.\run_sentinel.ps1
```

or manually

Backend

```bash
uvicorn backend.main:app --reload
```

Frontend

```bash
npm run dev
```

---

# 📂 Project Structure

```text
CodeSentinel/

├── agents/
├── backend/
├── core/
├── frontend/
├── fixtures/
├── logs/
├── tests/
├── data/
├── run_sentinel.ps1
├── setup_env.ps1
├── README.md
└── LICENSE
```

---

# 🧪 Validation

The repository includes automated validation suites for

- LLM Connectivity
- Self-Correction
- Red-Team Scenarios
- Performance Benchmarking
- Supply Chain Detection
- GitHub Repository Scanning

---

# 📸 Screenshots

> Add screenshots here after deployment.

- Landing Page
- Triage Center
- Live Agent Terminal
- Supply Chain Map
- Security Lab
- Executive Report
- GitHub Integration

---

# 🎯 Roadmap

- [x] AI Multi-Agent Security Analysis
- [x] GitHub Repository Scanner
- [x] Self-Correcting Detection
- [x] SBOM Intelligence
- [x] GitHub OAuth
- [x] Push to GitHub
- [x] Executive Reports
- [x] Production Deployment
- [ ] Multi-language Support
- [ ] Kubernetes Scanner
- [ ] Docker Image Scanner
- [ ] CVE Live Feed
- [ ] Team Collaboration
- [ ] CI/CD Integrations

---

# 📄 License

Licensed under the MIT License.

---

## 👨‍💻 Author

**Abeer Pathela**

If you found this project useful, consider giving it a ⭐ on GitHub.
