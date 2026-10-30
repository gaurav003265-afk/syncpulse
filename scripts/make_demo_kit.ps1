# ==============================================================================
# SyncPulse — Offline USB Demo Kit Builder
# ==============================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " BUILDING STANDALONE OFFLINE USB DEMO KIT (SYNCPULSE)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$KitDir = "demo_kit"
if (Test-Path $KitDir) {
    Remove-Item -Recurse -Force $KitDir
}
New-Item -ItemType Directory -Force -Path $KitDir | Out-Null

Write-Host "Copying core application files..." -ForegroundColor Yellow
Copy-Item -Recurse -Force core $KitDir\core
Copy-Item -Recurse -Force server $KitDir\server
Copy-Item -Recurse -Force web\dist $KitDir\web_dist
Copy-Item -Recurse -Force data\knowledge_pack $KitDir\data\knowledge_pack
Copy-Item -Recurse -Force data\synthetic_register $KitDir\data\synthetic_register
Copy-Item -Recurse -Force data\syncpulse $KitDir\data\syncpulse
Copy-Item -Recurse -Force eval $KitDir\eval
Copy-Item -Recurse -Force bench $KitDir\bench
Copy-Item -Recurse -Force docs $KitDir\docs
Copy-Item -Recurse -Force scripts $KitDir\scripts
Copy-Item -Force ask.py $KitDir\ask.py
Copy-Item -Force README.md $KitDir\README.md
Copy-Item -Force netlify.toml $KitDir\netlify.toml
Copy-Item -Force .env.example $KitDir\.env.example

Write-Host "Demo Kit successfully prepared in: $KitDir" -ForegroundColor Green
Write-Host "Copy this folder to a USB drive to run SyncPulse on any laptop with Python 3.11+." -ForegroundColor Gray
