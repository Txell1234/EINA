# Script para crear usuario en la plataforma OSINT
Write-Host "Creando usuario admin..." -ForegroundColor Yellow

$body = @{
    email = "admin@osint.local"
    password = "admin123"
    full_name = "Administrador"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/auth/register" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing
    
    if ($response.StatusCode -eq 201) {
        Write-Host ""
        Write-Host "Usuario creado exitosamente!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Credenciales de acceso:" -ForegroundColor Cyan
        Write-Host "   Email: admin@osint.local" -ForegroundColor White
        Write-Host "   Contrasena: admin123" -ForegroundColor White
    }
} catch {
    $errorResponse = $_.Exception.Response
    if ($errorResponse) {
        $reader = New-Object System.IO.StreamReader($errorResponse.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        
        if ($responseBody -like "*already registered*") {
            Write-Host ""
            Write-Host "El usuario ya existe" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Usa estas credenciales:" -ForegroundColor Cyan
            Write-Host "   Email: admin@osint.local" -ForegroundColor White
            Write-Host "   Contrasena: admin123" -ForegroundColor White
        } else {
            Write-Host ""
            Write-Host "Error: $responseBody" -ForegroundColor Red
        }
    } else {
        Write-Host ""
        Write-Host "Error: No se puede conectar al servidor" -ForegroundColor Red
        Write-Host "   Asegurate de que el backend este ejecutandose en http://localhost:8000" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Presiona cualquier tecla para continuar..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
