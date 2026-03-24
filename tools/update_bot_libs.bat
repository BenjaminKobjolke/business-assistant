@echo off
echo ========================================
echo  Business Assistant v2 - Update Bot Libraries
echo ========================================
echo.

where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: uv is not installed or not in PATH
    echo Please install uv first: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

echo Updating xmpp-bot to latest...
uv lock --upgrade-package xmpp-bot
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to update xmpp-bot
    pause
    exit /b 1
)

echo.
echo Updating telegram-bot to latest...
uv lock --upgrade-package telegram-bot
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to update telegram-bot
    pause
    exit /b 1
)

echo.
echo Syncing dependencies...
uv sync --all-extras
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to sync dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Bot libraries updated successfully!
echo ========================================
echo.
pause
