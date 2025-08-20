@REM #
@REM # SPDX-FileCopyrightText: Copyright (c) 1993-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
@REM # SPDX-License-Identifier: Apache-2.0
@REM #
@REM # Licensed under the Apache License, Version 2.0 (the "License");
@REM # you may not use this file except in compliance with the License.
@REM # You may obtain a copy of the License at
@REM #
@REM # http://www.apache.org/licenses/LICENSE-2.0
@REM #
@REM # Unless required by applicable law or agreed to in writing, software
@REM # distributed under the License is distributed on an "AS IS" BASIS,
@REM # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
@REM # See the License for the specific language governing permissions and
@REM # limitations under the License.
@REM #

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