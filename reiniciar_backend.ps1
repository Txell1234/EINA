# Script para reiniciar el servidor backend
Write-Host "Deteniendo servidores Python..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.ProcessName -eq "python" } | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

Write-Host "Cambiando al directorio backend..." -ForegroundColor Yellow
cd C:\Users\merit\Desktop\EINA\backend

# Agregar el directorio actual al PYTHONPATH para resolver imports
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
Write-Host "PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Gray

Write-Host "Iniciando servidor backend..." -ForegroundColor Green
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


