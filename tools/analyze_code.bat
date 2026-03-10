@echo off
if not exist "%~dp0analyze_code_config.bat" (
    echo ERROR: analyze_code_config.bat not found.
    echo Copy analyze_code_config.example.bat to analyze_code_config.bat and set your CLI_ANALYZER_PATH and LANGUAGE.
    exit /b 1
)
call "%~dp0analyze_code_config.bat"

set ANALYZER="%CLI_ANALYZER_PATH%\venv\Scripts\python.exe" "%CLI_ANALYZER_PATH%\main.py"
set ANALYZER_OPTS=--language %LANGUAGE% --verbosity minimal --maxamountoferrors 50

echo ============================================================
echo  Analyzing: business-assistant-v2
echo ============================================================
cd /d "%~dp0.."
%ANALYZER% %ANALYZER_OPTS% --path "." --output "code_analysis_results" --rules "code_analysis_rules.json"

set PLUGIN_BASE=%~dp0..\..

for %%P in (
    business-assistant-imap-plugin
    business-assistant-calendar-plugin
    business-assistant-rtm-plugin
) do (
    if exist "%PLUGIN_BASE%\%%P\code_analysis_rules.json" (
        echo.
        echo ============================================================
        echo  Analyzing: %%P
        echo ============================================================
        cd /d "%PLUGIN_BASE%\%%P"
        %ANALYZER% %ANALYZER_OPTS% --path "." --output "code_analysis_results" --rules "code_analysis_rules.json"
    ) else (
        echo.
        echo  Skipping %%P ^(no code_analysis_rules.json^)
    )
)

cd /d "%~dp0"
