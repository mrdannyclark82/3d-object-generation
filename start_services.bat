@echo off
setlocal enabledelayedexpansion

echo Starting LLM and Trellis services...

:: Check if conda environment exists
call conda env list | findstr "trellis" >nul
if errorlevel 1 (
    echo [ERROR] Conda environment 'trellis' not found!
    echo Please run install.bat first to set up the environment.
    pause
    exit /b 1
)

:: Start LLM service in background
echo Starting LLM service...
start /B cmd /c "call conda activate trellis && python nim_llm\run_llama.py"
if errorlevel 1 (
    echo [ERROR] Failed to start LLM service!
    pause
    exit /b 1
)

timeout /t 10 /nobreak

:: Start Trellis service in background
echo Starting Trellis service...
start /B cmd /c "call conda activate trellis && python nim_trellis\run_trellis.py"
if errorlevel 1 (
    echo [ERROR] Failed to start Trellis service!
    pause
    exit /b 1
)

echo.
echo Services started in background!
echo.
echo You can check the service logs:
echo - LLM logs: nim_llm\llama_container.log
echo - Trellis logs: nim_trellis\trellis_container.log
echo.
echo To check if services are ready, run: python check_services.py
echo.
pause 