@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title TalkLine Studio - Windows 11

echo ======================================
echo   TalkLine Studio - FREE LOCAL STARTER
 echo ======================================
echo.

rem Prefer Python 3.14 when installed, but allow recent Python 3 versions.
set "PYTHON_CMD="
py -3.14 --version >nul 2>&1 && set "PYTHON_CMD=py -3.14"
if not defined PYTHON_CMD (py -3.13 --version >nul 2>&1 && set "PYTHON_CMD=py -3.13")
if not defined PYTHON_CMD (py -3.12 --version >nul 2>&1 && set "PYTHON_CMD=py -3.12")
if not defined PYTHON_CMD (py -3.11 --version >nul 2>&1 && set "PYTHON_CMD=py -3.11")
if not defined PYTHON_CMD (python --version >nul 2>&1 && set "PYTHON_CMD=python")
if not defined PYTHON_CMD (
  echo ERROR: Python 3.11 or newer is not available in PATH.
  echo Open Command Prompt and check: py -3.14 --version
  goto :error
)

echo [1/3] Checking Python...
%PYTHON_CMD% --version
if errorlevel 1 goto :error

if not exist ".venv\Scripts\python.exe" (
  echo Creating a private environment for TalkLine Studio...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto :error
)

echo [2/3] Checking free dependencies...
".venv\Scripts\python.exe" -c "import streamlit, pptx, PIL, imageio_ffmpeg, jsonschema, pypdfium2" >nul 2>&1
if errorlevel 1 (
  echo Installing missing packages. Internet needed only for initial setup.
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :error
)

echo [3/3] Starting TalkLine Studio...
".venv\Scripts\python.exe" scripts\start_ollama.py
echo Your browser should open at http://127.0.0.1:8501
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Startup failed. Copy the full error message for troubleshooting.
echo If Python 3.14 dependencies fail, we can use Python 3.12 in a virtual environment without uninstalling 3.14.
pause
exit /b 1
