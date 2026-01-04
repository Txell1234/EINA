$headers = @{
    "Content-Type" = "application/json"
}

$body = @{
    email = "admin@osint.com"
    password = "admin123"
    full_name = "admin"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/register" -Method POST -Headers $headers -Body $body
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  USUARIO CREADO EXITOSAMENTE" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "ID: $($response.id)" -ForegroundColor Cyan
    Write-Host "Email: $($response.email)" -ForegroundColor Cyan
    Write-Host "Full Name: $($response.full_name)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Ahora puedes iniciar sesion en:" -ForegroundColor Yellow
    Write-Host "  http://localhost:3002" -ForegroundColor White
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 400) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host "  EL USUARIO YA EXISTE" -ForegroundColor Yellow
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "El usuario ya esta creado. Puedes iniciar sesion:" -ForegroundColor Cyan
        Write-Host "  http://localhost:3002" -ForegroundColor White
        Write-Host ""
        Write-Host "Credenciales:" -ForegroundColor Yellow
        Write-Host "  Email: admin@osint.com" -ForegroundColor White
        Write-Host "  Password: admin123" -ForegroundColor White
    } else {
        Write-Host ""
        Write-Host "Error: $statusCode" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
}









