$ErrorActionPreference = "Stop"

$ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollama)) {
    throw "Ollama executable not found at $ollama"
}

Get-Process | Where-Object { $_.ProcessName -like "ollama*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$env:OLLAMA_LLM_LIBRARY = "cpu_avx2"
$env:OLLAMA_NO_GPU = "1"

Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
Start-Sleep -Seconds 5

Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 10 | Out-Null
Write-Host "Ollama is running in CPU mode with OLLAMA_LLM_LIBRARY=cpu_avx2." -ForegroundColor Green
