@echo off
title Businness Assistant

echo ========================================
echo  Business Assistant v2 - Starting
echo ========================================
echo.

:: Check if uv is installed
where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: uv is not installed or not in PATH
    echo Please install uv first: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

uv run python -m business_assistant.main
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Application exited with error
    pause
    exit /b 1
)

