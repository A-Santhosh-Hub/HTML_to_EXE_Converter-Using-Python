@echo off
:: ═══════════════════════════════════════════════════════
::  SanStudio — CLI Build (no GUI)
::  Usage: build_cli.bat [args passed to build_cli.py]
::  Example: build_cli.bat --input ./my_project --output ./dist --name MyApp
:: ═══════════════════════════════════════════════════════
python build_cli.py %*
if %errorlevel% neq 0 pause
