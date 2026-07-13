param(
    [switch]$Install,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = "Stop"

function Test-PythonCandidate {
    param([string]$Command)

    try {
        $null = & $Command -c "import sys, tempfile; print(sys.executable)" 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Resolve-HealthyPython {
    $candidates = @(
        "py -3.12",
        "py -3.13",
        "python",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -like "py -*") {
            $parts = $candidate.Split(" ")
            try {
                $null = & $parts[0] $parts[1] -c "import sys, tempfile; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    return $candidate
                }
            } catch {
                continue
            }
        } elseif (Test-Path $candidate) {
            if (Test-PythonCandidate $candidate) {
                return $candidate
            }
        } elseif ($candidate -eq "python" -and (Get-Command python -ErrorAction SilentlyContinue)) {
            if (Test-PythonCandidate $candidate) {
                return $candidate
            }
        }
    }

    throw "No healthy Python was found. Install Python 3.12+ or repair the Python that is first on PATH."
}

function Invoke-HealthyPython {
    param(
        [string]$PythonCommand,
        [string[]]$Arguments
    )

    if ($PythonCommand -like "py -*") {
        $parts = $PythonCommand.Split(" ")
        & $parts[0] $parts[1] @Arguments
    } else {
        & $PythonCommand @Arguments
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonCommand = Resolve-HealthyPython
Write-Host "Using Python: $pythonCommand" -ForegroundColor Cyan

if ($Install) {
    Invoke-HealthyPython $pythonCommand @("-m", "pip", "install", "-r", "$repoRoot\cli\requirements.txt")
    exit $LASTEXITCODE
}

$arguments = @("$repoRoot\cli\main.py") + $CliArgs
Invoke-HealthyPython $pythonCommand $arguments
