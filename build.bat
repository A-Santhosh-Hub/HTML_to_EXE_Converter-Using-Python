@echo off
:: ════════════════════════════════════════════════════════
::  SanStudio HTML → EXE Converter
::  Developed by Santhosh A
::  https://a-santhosh-hub.github.io/in/
:: ════════════════════════════════════════════════════════

title SanStudio Converter — Launcher

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   SanStudio HTML ^→ EXE Converter            ║
echo  ║   Developed by Santhosh A                   ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found. Please install Python 3.12+
    echo          https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check for dependencies
python -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo  [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo  [OK] Launching SanConverter...
echo.

:: Launch GUI
python builder_app.py

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Application crashed. See error above.
    pause
)
