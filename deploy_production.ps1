# CodeSentinel Production Deployment
# Usage: .\deploy_production.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Green
Write-Host "  CodeSentinel Production Deploy" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

function Test-RequiredEnv {
    param([string[]]$Keys)
    $envFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envFile)) {
        Write-Error ".env not found. Copy .env.example and configure required keys."
    }
    $lines = Get-Content $envFile | Where-Object { $_ -match "=" -and $_ -notmatch "^\s*#" }
    $map = @{}
    foreach ($line in $lines) {
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) { $map[$parts[0].Trim()] = $parts[1].Trim() }
    }
    $missing = @()
    foreach ($key in $Keys) {
        if (-not $map.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($map[$key])) {
            $missing += $key
        }
    }
    if ($missing.Count -gt 0) {
        Write-Error ("Missing required .env keys: " + ($missing -join ", "))
    }
    Write-Host "[OK] Required environment keys present" -ForegroundColor Green
}

Test-RequiredEnv -Keys @(
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET",
    "SENTINEL_APP_URL",
    "FRONTEND_URL"
)

if (-not (Test-Path "$ProjectRoot\.venv\Scripts\Activate.ps1")) {
    Write-Host "==> Bootstrapping Python environment..." -ForegroundColor Yellow
    & "$ProjectRoot\setup_env.ps1"
}

Write-Host "==> Installing backend dependencies..." -ForegroundColor Yellow
Push-Location $ProjectRoot
.\.venv\Scripts\pip.exe install -q -r backend\requirements.txt
Pop-Location

Write-Host "==> Building React frontend (dist/)..." -ForegroundColor Yellow
Push-Location "$ProjectRoot\frontend"
if (-not (Test-Path "node_modules")) { npm install }
$env:NODE_ENV = "production"
npm run build
if (-not (Test-Path "dist")) { Write-Error "Frontend build failed — dist/ not found." }
Pop-Location
Write-Host "[OK] Frontend built to frontend/dist" -ForegroundColor Green

Write-Host "==> Starting backend (production mode)..." -ForegroundColor Green
Push-Location $ProjectRoot
$env:ENVIRONMENT = "production"
$env:LOG_LEVEL = "WARNING"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level warning
Pop-Location
