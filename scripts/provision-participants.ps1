<#
.SYNOPSIS
  Fallback: provision N participant resource groups in the instructor's subscription.

.DESCRIPTION
  When a participant cannot run `azd up` (quota, permissions, network), the
  instructor uses this script to provision a dedicated resource group for them.
  Each participant gets their own resourceToken / environment name and a
  per-participant `.env` file they can drop into their local clone.

.PARAMETER Count
  Number of participants to provision.

.PARAMETER Location
  Azure region (default swedencentral — where we have quota).

.PARAMETER Prefix
  Environment name prefix (default foundry-).

.EXAMPLE
  ./provision-participants.ps1 -Count 18 -Location swedencentral

  Provisions 18 RGs named rg-foundry-01 ... rg-foundry-18 in parallel
  and writes per-participant .env files under ./out/.
#>
[CmdletBinding()]
param(
    [int]$Count = 18,
    [string]$Location = "swedencentral",
    [string]$Prefix = "foundry-",
    [string]$ResourceGroupPrefix = "rg-foundry",
    [int]$Parallelism = 6
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path "$PSScriptRoot/.."
$outDir = Join-Path $repoRoot "out"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

Write-Host "Provisioning $Count participant environments in $Location..." -ForegroundColor Cyan

$participants = @()
for ($i = 1; $i -le $Count; $i++) {
  $suffix = "{0:00}" -f $i
  $participants += [pscustomobject]@{
    EnvName = "{0}{1}" -f $Prefix, $suffix
    ResourceGroup = "{0}-{1}" -f $ResourceGroupPrefix, $suffix
  }
}

# Run in parallel batches
$participants | ForEach-Object -ThrottleLimit $Parallelism -Parallel {
  $envName = $_.EnvName
  $resourceGroup = $_.ResourceGroup
    $repoRoot = $using:repoRoot
    $outDir = $using:outDir
    $location = $using:Location

  Write-Host "[$envName / $resourceGroup] starting..." -ForegroundColor Yellow
    Push-Location $repoRoot
    try {
        # Use azd directly so each env has its own state
        $env:AZURE_ENV_NAME = $envName
    & az group create --name $resourceGroup --location $location --tags workshop=foundry-workshop 2>&1 | Out-Null
        & azd env new $envName --no-prompt 2>&1 | Out-Null
        & azd env select $envName 2>&1 | Out-Null
        & azd env set AZURE_LOCATION $location 2>&1 | Out-Null
    & azd env set AZURE_RESOURCE_GROUP $resourceGroup 2>&1 | Out-Null
        & azd provision --no-prompt 2>&1 | Tee-Object -FilePath (Join-Path $outDir "$envName.log")

        # Capture outputs for the participant
        $envFile = Join-Path $outDir "$envName.env"
        & azd env get-values > $envFile
        Write-Host "[$envName] DONE -> $envFile" -ForegroundColor Green
    } catch {
        Write-Host "[$envName] FAILED: $_" -ForegroundColor Red
    } finally {
        Pop-Location
    }
}

Write-Host "`nAll done. Per-participant .env files in $outDir" -ForegroundColor Cyan
Write-Host "Share each .env with the corresponding participant." -ForegroundColor Cyan
