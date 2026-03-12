@echo off
title Usage Report

echo ========================================
echo  Business Assistant v2 - Usage Report
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

uv run python -m tools.log_analyze %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Usage report exited with error
    pause
    exit /b 1
)

pause
