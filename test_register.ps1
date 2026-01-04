$body = '{"email":"admin@osint.com","password":"admin123","full_name":"admin"}'
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/register" -Method POST -ContentType "application/json" -Body $body
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  USUARIO CREADO EXITOSAMENTE" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "ID: $($response.id)" -ForegroundColor Cyan
    Write-Host "Email: $($response.email)" -ForegroundColor Cyan
    Write-Host "Full Name: $($response.full_name)" -ForegroundColor Cyan
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    $stream = $_.Exception.Response.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($stream)
    $responseBody = $reader.ReadToEnd()
    Write-Host ""
    Write-Host "Error $statusCode" -ForegroundColor Red
    Write-Host $responseBody -ForegroundColor Red
}









