<#
.SYNOPSIS
  Tear down all participant environments created by provision-participants.ps1.
#>
[CmdletBinding()]
param(
    [string]$Prefix = "foundry-p",
    [int]$Parallelism = 6,
    [switch]$Purge
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path "$PSScriptRoot/.."

$envs = & azd env list --output json | ConvertFrom-Json
$matching = $envs | Where-Object { $_.Name -like "$Prefix*" }

Write-Host "Tearing down $($matching.Count) participant environment(s)" -ForegroundColor Cyan

$matching | ForEach-Object -ThrottleLimit $Parallelism -Parallel {
    $envName = $_.Name
    $repoRoot = $using:repoRoot
    $purge = $using:Purge
    Push-Location $repoRoot
    try {
        & azd env select $envName 2>&1 | Out-Null
        if ($purge) {
            & azd down --force --purge 2>&1
        } else {
            & azd down --force 2>&1
        }
        Write-Host "[$envName] down" -ForegroundColor Green
    } catch {
        Write-Host "[$envName] FAILED: $_" -ForegroundColor Red
    } finally {
        Pop-Location
    }
}
