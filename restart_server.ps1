# Script para reiniciar el servidor backend
# Ejecutar desde la raíz del proyecto

Write-Host "`n🛑 Deteniendo procesos de uvicorn..." -ForegroundColor Yellow

# Detener procesos de Python que ejecutan uvicorn
$processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*" -or $_.Path -like "*python*"
}
if ($processes) {
    foreach ($proc in $processes) {
        try {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Write-Host "   Proceso $($proc.Id) detenido" -ForegroundColor Gray
        } catch {
            # Ignorar errores
        }
    }
    Start-Sleep -Seconds 2
}

Write-Host "✅ Procesos detenidos`n" -ForegroundColor Green

Write-Host "🚀 Iniciando servidor backend..." -ForegroundColor Cyan
Write-Host "📁 Directorio: $PWD\backend`n" -ForegroundColor Gray

# Cambiar al directorio backend e iniciar servidor
Set-Location backend

# Agregar el directorio actual al PYTHONPATH para resolver imports
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
Write-Host "PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Gray
Write-Host ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


