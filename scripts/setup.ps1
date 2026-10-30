# ==============================================================================
# H5 Frontline Companion - Setup Script (Windows PowerShell)
# ==============================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " TALENT AP MEGA HACKATHON 2026 - PROBLEM H5 ENVIRONMENT SETUP" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Virtual Environment Setup
if (-not (Test-Path ".venv")) {
    Write-Host "[1/4] Creating virtual environment (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "[1/4] Virtual environment (.venv) already exists." -ForegroundColor Green
}

# 2. Dependency Installation
Write-Host "[2/4] Installing minimal dependencies..." -ForegroundColor Yellow
& .venv\Scripts\pip install --upgrade pip
& .venv\Scripts\pip install fastapi uvicorn pydantic psutil pytest httpx

# 3. Build Knowledge Pack
Write-Host "[3/4] Building offline knowledge pack from protocols..." -ForegroundColor Yellow
& .venv\Scripts\python -m core.build_pack

# 4. Initialize SQLite Household Register
Write-Host "[4/4] Initializing local SQLite register..." -ForegroundColor Yellow
& .venv\Scripts\python -c "from core.visits import VisitScheduler; vs = VisitScheduler(); print('Households in DB:', vs.get_total_count())"

Write-Host "`nSetup complete! You can now run the demo with: powershell scripts/run_demo.ps1`n" -ForegroundColor Green
