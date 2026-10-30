# ==============================================================================
# SyncPulse — Healthcare Connected. Even Offline.
# ASHA & Rural Healthcare Platform Demo Launcher (Windows PowerShell)
# ==============================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " SYNCPULSE — OFFLINE-FIRST ASHA HEALTHCARE PLATFORM (DEMO)" -ForegroundColor Cyan
Write-Host " Tagline: Healthcare Connected. Even Offline." -ForegroundColor Gray
Write-Host "======================================================================" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Error: Virtual environment not found. Please run scripts/setup.ps1 first." -ForegroundColor Red
    exit 1
}

# Ensure knowledge pack exists
if (-not (Test-Path "data\knowledge_pack\bm25_index.json")) {
    Write-Host "Building offline knowledge pack..." -ForegroundColor Yellow
    & .venv\Scripts\python -m core.build_pack
}

Write-Host "`nStarting SyncPulse Local Server on http://localhost:8000 ..." -ForegroundColor Green
Write-Host "Serving PWA Frontend (Patient Portal + 6-Module ASHA Dashboard) directly from web/dist." -ForegroundColor Gray
Write-Host "Press Ctrl+C to terminate the server.`n" -ForegroundColor Yellow

# Launch browser after a brief delay
Start-Process "http://localhost:8000"

# Run Uvicorn server hosting FastAPI + PWA
& .venv\Scripts\python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
