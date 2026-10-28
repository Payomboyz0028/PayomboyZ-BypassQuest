@echo off
title KeyBypass Discord Bot + API Server
cd /d "%~dp0"
echo ========================================================
echo Starting KeyBypass Discord Bot + Multi-Engine API...
echo ========================================================
python -u main.py
if %ERRORLEVEL% NEQ 0 (
    echo [!] Bot exited with error code %ERRORLEVEL%.
    pause
)
