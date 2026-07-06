<#
.SYNOPSIS
  Remove numbered Entra users created for workshop participants.

.DESCRIPTION
  Deletes users named <UserPrefix>-01@<tenant-domain>,
  <UserPrefix>-02@<tenant-domain>, etc. If -UserDomain is omitted, the script
  uses the tenant's verified initial .onmicrosoft.com domain, falling back to
  the tenant's default verified domain.

.EXAMPLE
  ./scripts/remove-participant-users.ps1 -Count 25
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [int]$Count = 25,
    [string]$UserDomain,
    [string]$UserPrefix = 'foundry',
    [string]$Subscription
)

$ErrorActionPreference = 'Stop'

if ($Subscription) {
    az account set --subscription $Subscription | Out-Null
}

function Invoke-AzCliJson {
    param([string[]]$Arguments)

    $output = & az @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ($output | Out-String)
    }
    return $output
}

function Resolve-DefaultUserDomain {
    $domainsJson = Invoke-AzCliJson -Arguments @(
        'rest',
        '--method', 'GET',
        '--url', 'https://graph.microsoft.com/v1.0/domains?$select=id,isDefault,isInitial,isVerified',
        '--query', 'value',
        '-o', 'json'
    )
    $domains = $domainsJson | ConvertFrom-Json
    if (-not $domains) {
        throw 'Could not discover tenant domains. Pass -UserDomain explicitly.'
    }

    $initialDomain = $domains | Where-Object { $_.isVerified -and $_.isInitial } | Select-Object -First 1
    if ($initialDomain) { return $initialDomain.id }

    $defaultDomain = $domains | Where-Object { $_.isVerified -and $_.isDefault } | Select-Object -First 1
    if ($defaultDomain) { return $defaultDomain.id }

    throw 'Could not find a verified initial or default tenant domain. Pass -UserDomain explicitly.'
}

if (-not $UserDomain) {
    $UserDomain = Resolve-DefaultUserDomain
    Write-Host "Using tenant domain $UserDomain for participant users" -ForegroundColor Cyan
}

for ($participantNumber = 1; $participantNumber -le $Count; $participantNumber++) {
    $suffix = '{0:D2}' -f $participantNumber
    $userPrincipalName = "$UserPrefix-$suffix@$UserDomain"
    $objectId = az ad user show --id $userPrincipalName --query id -o tsv 2>$null

    if (-not $objectId) {
        Write-Host "[$suffix] $userPrincipalName not found" -ForegroundColor Yellow
        continue
    }

    if ($PSCmdlet.ShouldProcess($userPrincipalName, 'Delete Entra user')) {
        az ad user delete --id $objectId | Out-Null
        Write-Host "[$suffix] deleted $userPrincipalName" -ForegroundColor Green
    }
}