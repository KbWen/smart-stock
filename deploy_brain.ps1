Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

param(
    [string]$Target = '.'
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bashScript = Join-Path $scriptDir 'deploy_brain.sh'

if (-not (Test-Path -Path $bashScript -PathType Leaf)) {
    Write-Error "cannot find deploy script: $bashScript"
    exit 1
}

$bashCmd = Get-Command bash -ErrorAction SilentlyContinue
if (-not $bashCmd) {
    Write-Error 'bash is not installed. Install Git Bash or WSL, then rerun deploy_brain.ps1.'
    exit 1
}

& $bashCmd.Source $bashScript $Target
exit $LASTEXITCODE