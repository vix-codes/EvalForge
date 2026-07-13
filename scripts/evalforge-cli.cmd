@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0evalforge_cli.ps1" %*
exit /b %ERRORLEVEL%
