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
