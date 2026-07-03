# Provision the workshop infrastructure into an existing (or to-be-created)
# resource group. Idempotent — safe to re-run.
#
# Usage (PowerShell):
#   ./scripts/provision-rg.ps1 -ResourceGroup rg-foundry-alice `
#                              -Location swedencentral `
#                              -EnvName foundry-alice `
#                              [-Subscription <sub-id>] `
#                              [-PrincipalId <object-id>] `
#                              [-DeployRealtimeModel]
#
# What it does:
#   1. Ensures the RG exists (creates it if not).
#   2. Initialises or reuses the azd environment $EnvName.
#   3. Sets AZURE_LOCATION + AZURE_RESOURCE_GROUP in the azd env so azd
#      deploys into the existing RG instead of creating a new one.
#   4. Runs `azd provision`.
#
# If `azd` does not deploy into the existing RG correctly, fall back to:
#   az deployment group create \
#       --resource-group $ResourceGroup \
#       --template-file infra/main.bicep \
#       --parameters infra/main.parameters.json \
#       --parameters environmentName=$EnvName principalId=<oid>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ResourceGroup,
    [string]$Location = 'swedencentral',
    [string]$EnvName,
    [string]$Subscription,
    [string]$PrincipalId,
    [switch]$DeployRealtimeModel
)

$ErrorActionPreference = 'Stop'

if (-not $EnvName) { $EnvName = $ResourceGroup }

if ($Subscription) {
    Write-Host "Selecting subscription $Subscription"
    az account set --subscription $Subscription | Out-Null
}

$rgExists = az group exists --name $ResourceGroup
if ($rgExists -ne 'true') {
    Write-Host "Creating resource group $ResourceGroup in $Location"
    az group create --name $ResourceGroup --location $Location --tags workshop=foundry-workshop | Out-Null
} else {
    Write-Host "Resource group $ResourceGroup already exists"
}

# Make sure we are at the repo root (parent of scripts/)
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# Initialise or refresh azd environment
$envList = (azd env list --output json 2>$null) | ConvertFrom-Json
$haveEnv = $false
if ($envList) {
    foreach ($e in $envList) { if ($e.Name -eq $EnvName) { $haveEnv = $true } }
}
if (-not $haveEnv) {
    Write-Host "Creating azd environment $EnvName"
    azd env new $EnvName --location $Location
} else {
    Write-Host "Reusing azd environment $EnvName"
    azd env select $EnvName
}

azd env set AZURE_LOCATION $Location
azd env set AZURE_RESOURCE_GROUP $ResourceGroup
$deployRealtimeModelValue = if ($DeployRealtimeModel.IsPresent) { 'true' } else { 'false' }
azd env set DEPLOY_REALTIME_MODEL $deployRealtimeModelValue

if ($PrincipalId) {
    azd env set AZURE_PRINCIPAL_ID $PrincipalId
}

Write-Host "Running azd provision against $ResourceGroup"
azd provision

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "azd provision failed. Fallback: run the bicep directly."
    Write-Host "  az deployment group create -g $ResourceGroup ``"
    Write-Host "      --template-file infra/main.bicep ``"
    Write-Host "      --parameters infra/main.parameters.json ``"
    Write-Host "      --parameters environmentName=$EnvName"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Provisioning complete."
Write-Host "Next step: ./scripts/postdeploy-rbac.ps1 -ResourceGroup $ResourceGroup -Principals <upn-or-oid>[,...]"
