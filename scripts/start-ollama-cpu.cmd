@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_ollama_cpu.ps1"
exit /b %ERRORLEVEL%
