@echo off
cd /d "%~dp0.."
uv run python -m tools.log_analyze %*
