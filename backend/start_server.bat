@echo off
echo ============================================================
echo INICIANDO SERVIDOR BACKEND
echo ============================================================
echo.
cd /d %~dp0
echo Directorio: %CD%
echo.

REM Agregar el directorio actual al PYTHONPATH para resolver imports
set PYTHONPATH=%CD%;%PYTHONPATH%
echo PYTHONPATH: %PYTHONPATH%
echo.

echo Iniciando servidor en http://0.0.0.0:8000...
echo.
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause


