@echo off
setlocal enabledelayedexpansion

echo Stopping LLM and Trellis services...

:: Stop LLM container
echo Stopping LLM container...
call conda run -n trellis --no-capture-output python -c "from nim_llm.manager import stop_container; stop_container()"
if errorlevel 1 (
    echo [WARNING] Failed to stop LLM container gracefully
)

:: Stop Trellis container
echo Stopping Trellis container...
call conda run -n trellis --no-capture-output python -c "from nim_trellis.manager import stop_container; stop_container()"
if errorlevel 1 (
    echo [WARNING] Failed to stop Trellis container gracefully
)

:: Kill any remaining Python processes that might be running the services
echo Stopping Python processes...
taskkill /f /im python.exe 2>nul
if errorlevel 1 (
    echo No Python processes found to stop
) else (
    echo Python processes stopped
)

echo.
echo Services stopped!
echo.
pause 