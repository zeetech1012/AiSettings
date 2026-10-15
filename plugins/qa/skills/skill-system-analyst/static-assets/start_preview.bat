@echo off
cd /d "%~dp0"
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Node.js is not installed.
    pause
    exit /b 1
)
node server.js
pause
