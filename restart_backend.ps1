# Script para reiniciar el servidor backend
# Ejecutar desde la raíz del proyecto (C:\Users\merit\Desktop\EINA)

Write-Host "🛑 Deteniendo servidor backend si está corriendo..." -ForegroundColor Yellow

# Detener procesos de uvicorn en el puerto 8000
$processes = Get-Process | Where-Object {$_.ProcessName -eq "python" -and $_.CommandLine -like "*uvicorn*"}
if ($processes) {
    $processes | Stop-Process -Force
    Write-Host "✅ Procesos anteriores detenidos" -ForegroundColor Green
    Start-Sleep -Seconds 2
}

Write-Host "`n🚀 Iniciando servidor backend..." -ForegroundColor Cyan
Write-Host "📁 Directorio: $PWD\backend" -ForegroundColor Gray

# Cambiar al directorio backend e iniciar servidor
Set-Location backend

# Agregar el directorio actual al PYTHONPATH para resolver imports
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
Write-Host "PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Gray

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


