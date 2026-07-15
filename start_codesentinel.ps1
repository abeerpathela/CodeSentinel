# CodeSentinel — 1-click startup (Backend + Frontend)
# Usage: .\start_codesentinel.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host "==> CodeSentinel Phase 4 Launcher" -ForegroundColor Cyan

# Ensure Python venv
if (-not (Test-Path "$ProjectRoot\.venv\Scripts\python.exe")) {
    Write-Host "==> Bootstrapping Python environment..." -ForegroundColor Yellow
    & "$ProjectRoot\setup_env.ps1"
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

# Ensure frontend deps
if (-not (Test-Path "$ProjectRoot\frontend\node_modules")) {
    Write-Host "==> Installing frontend dependencies (npm)..." -ForegroundColor Yellow
    Push-Location "$ProjectRoot\frontend"
    npm install
    Pop-Location
}

Write-Host "==> Starting FastAPI backend on http://127.0.0.1:8000" -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$ProjectRoot'; .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"
) -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host "==> Starting Vite dashboard on http://127.0.0.1:5173" -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$ProjectRoot\frontend'; npm run dev"
) -WindowStyle Normal

Write-Host ""
Write-Host "  Backend:   http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "  Dashboard: http://127.0.0.1:5173" -ForegroundColor Cyan
Write-Host "  Analytics: http://127.0.0.1:8000/analytics/summary" -ForegroundColor Cyan
Write-Host ""
