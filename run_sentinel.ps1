# CodeSentinel - 1-Click Sentinel Command and Control Launcher
# Usage: .\run_sentinel.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CodeSentinel - Sentinel C&C Launcher  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path "$ProjectRoot\.venv\Scripts\Activate.ps1")) {
    Write-Host "==> Bootstrapping Python environment..." -ForegroundColor Yellow
    & "$ProjectRoot\setup_env.ps1"
}

if (-not (Test-Path "$ProjectRoot\frontend\node_modules")) {
    Write-Host "==> Installing frontend dependencies..." -ForegroundColor Yellow

    Push-Location "$ProjectRoot\frontend"
    npm install
    Pop-Location
}

Write-Host "==> Activating virtual environment" -ForegroundColor Green
. "$ProjectRoot\.venv\Scripts\Activate.ps1"

Write-Host "==> Starting FastAPI backend -> http://127.0.0.1:8000" -ForegroundColor Green

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ProjectRoot'; .\.venv\Scripts\Activate.ps1; python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"
)

Start-Sleep -Seconds 2

Write-Host "==> Starting Vite dashboard -> http://127.0.0.1:5173" -ForegroundColor Green

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ProjectRoot\frontend'; npm run dev"
)

Write-Host ""
Write-Host "Dashboard:  http://127.0.0.1:5173" -ForegroundColor Cyan
Write-Host "API Docs:   http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "Resilience: http://127.0.0.1:8000/analytics/resilience" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services are live. Press Ctrl+C in each window to stop." -ForegroundColor Yellow
