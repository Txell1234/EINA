$body = '{"email":"admin@osint.com","password":"admin123","full_name":"Administrador"}'
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/register" -Method POST -ContentType "application/json" -Body $body
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  USUARIO CREADO EXITOSAMENTE" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Credenciales:" -ForegroundColor Cyan
    Write-Host "  Email:    admin@osint.com" -ForegroundColor White
    Write-Host "  Password: admin123" -ForegroundColor White
    Write-Host ""
    Write-Host "Inicia sesion: http://localhost:3000" -ForegroundColor Yellow
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 400) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host "  USUARIO YA EXISTE" -ForegroundColor Yellow
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Credenciales:" -ForegroundColor Cyan
        Write-Host "  Email:    admin@osint.com" -ForegroundColor White
        Write-Host "  Password: admin123" -ForegroundColor White
        Write-Host ""
        Write-Host "Inicia sesion: http://localhost:3000" -ForegroundColor Yellow
    } else {
        Write-Host ""
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Status: $statusCode" -ForegroundColor Red
    }
}









