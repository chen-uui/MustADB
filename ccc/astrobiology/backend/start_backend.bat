@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE=python"
if exist "%~dp0..\..\..\.venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0..\..\..\.venv\Scripts\python.exe"
if "%BACKEND_PORT%"=="" set "BACKEND_PORT=8000"
echo Starting Django backend on port %BACKEND_PORT%
"%PYTHON_EXE%" manage.py runserver %BACKEND_PORT%
pause
