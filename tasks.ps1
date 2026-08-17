<#
.SYNOPSIS
    Task runner for ReefCommand on Windows.

.DESCRIPTION
    The same commands are also listed in README.md and can be run by hand.
    Usage:  .\tasks.ps1 <task>

.EXAMPLE
    .\tasks.ps1 setup
    .\tasks.ps1 check
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet('help', 'setup', 'api', 'web', 'lint', 'fmt', 'test', 'test-e2e', 'check', 'prefetch', 'clean')]
    [string]$Task = 'help'
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

function Invoke-In($dir, $command) {
    Push-Location (Join-Path $root $dir)
    try { Invoke-Expression $command } finally { Pop-Location }
}

switch ($Task) {
    'help' {
        Write-Host 'setup     Install backend and frontend dependencies'
        Write-Host 'api       Run the backend API with reload'
        Write-Host 'web       Run the dashboard dev server'
        Write-Host 'lint      Ruff check plus eslint plus tsc'
        Write-Host 'fmt       Ruff format plus prettier'
        Write-Host 'test      Backend unit and integration tests'
        Write-Host 'test-e2e  Backend end-to-end tests'
        Write-Host 'check     Everything CI runs'
        Write-Host 'prefetch  Cache external data for the demo window'
        Write-Host 'clean     Remove caches and build output'
    }
    'setup' {
        Invoke-In 'backend' 'uv sync'
        Invoke-In 'frontend' 'npm install'
    }
    'api'      { Invoke-In 'backend' 'uv run uvicorn reefcommand.api.app:app --reload' }
    'web'      { Invoke-In 'frontend' 'npm run dev' }
    'lint' {
        Invoke-In 'backend' 'uv run ruff check .'
        Invoke-In 'frontend' 'npm run lint; npm run typecheck'
    }
    'fmt' {
        Invoke-In 'backend' 'uv run ruff format .'
        Invoke-In 'frontend' 'npm run format'
    }
    'test'     { Invoke-In 'backend' 'uv run pytest tests/unit tests/integration' }
    'test-e2e' { Invoke-In 'backend' 'uv run pytest tests/e2e' }
    'check' {
        & $PSCommandPath 'lint'
        & $PSCommandPath 'test'
        & $PSCommandPath 'test-e2e'
    }
    'prefetch' { Invoke-In 'backend' 'uv run python ../scripts/prefetch_external_data.py' }
    'clean' {
        Get-ChildItem -Path $root -Recurse -Directory -Filter '__pycache__' |
            Remove-Item -Recurse -Force
        foreach ($p in 'backend\.pytest_cache', 'backend\.ruff_cache', 'frontend\dist') {
            $full = Join-Path $root $p
            if (Test-Path $full) { Remove-Item $full -Recurse -Force }
        }
    }
}
