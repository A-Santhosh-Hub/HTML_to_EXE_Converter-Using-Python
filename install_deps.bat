@echo off
:: ════════════════════════════════════════════════════════
::  SanStudio — Dependency Installer
::  Run this ONCE before first use
:: ════════════════════════════════════════════════════════

title SanStudio — Installing Dependencies

echo.
echo  Installing SanConverter dependencies...
echo  This may take 2-5 minutes on first run.
echo.

pip install customtkinter pyinstaller pywebview Pillow Jinja2 tkinterdnd2

echo.
echo  ════════════════════════════════════════════
echo  Installation complete!
echo  Run build.bat to launch the converter.
echo  ════════════════════════════════════════════
echo.
pause
