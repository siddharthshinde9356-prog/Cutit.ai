@echo off
title Cutit ai - AI Background Remover Studio
cd /d "%~dp0"

echo Starting Cutit ai Studio...
if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" app.py
) else (
    echo [ERROR] Virtual environment not found at .venv
    pause
)
