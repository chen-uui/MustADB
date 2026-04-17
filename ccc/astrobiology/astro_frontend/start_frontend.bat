@echo off
setlocal
cd /d "%~dp0"
if "%FRONTEND_PORT%"=="" set "FRONTEND_PORT=5173"
echo Starting Vite frontend on port %FRONTEND_PORT%
npm.cmd run dev -- --port %FRONTEND_PORT%
pause
