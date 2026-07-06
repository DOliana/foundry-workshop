<#
.SYNOPSIS
  Create numbered Entra users for workshop participants and grant each one
  Owner on their matching numbered resource group.

.DESCRIPTION
    Creates users named <UserPrefix>-01@<tenant-domain>,
    <UserPrefix>-02@<tenant-domain>, etc., and grants each user Owner on
    rg-foundry-01, rg-foundry-02, etc. If -UserDomain is omitted, the script uses
    the tenant's verified initial .onmicrosoft.com domain, falling back to the
    tenant's default verified domain.

  MFA is controlled by tenant-wide security defaults and Conditional Access
  policies, not by user creation. If your tenant admin has prepared a temporary
  Conditional Access exclusion or grace-period group for the workshop, pass its
  object id with -MfaExclusionGroupId and this script will add each user to it.

.EXAMPLE
    ./scripts/create-participant-users.ps1 -Count 25

.EXAMPLE
  ./scripts/create-participant-users.ps1 -Count 25 `
      -MfaExclusionGroupId 00000000-0000-0000-0000-000000000000
#>
[CmdletBinding()]
param(
    [int]$Count = 25,
    [string]$UserDomain,
    [string]$UserPrefix = 'foundry',
    [string]$ResourceGroupPrefix = 'rg-foundry',
    [string]$Location = 'swedencentral',
    [string]$Subscription,
    [string]$OutputPath,
    [string]$MfaExclusionGroupId,
    [switch]$ResetExistingPasswords,
    [switch]$ForceChangePasswordNextSignIn
)

$ErrorActionPreference = 'Stop'

if ($Subscription) {
    az account set --subscription $Subscription | Out-Null
}

$repoRoot = Resolve-Path "$PSScriptRoot/.."
if (-not $OutputPath) {
    $outDir = Join-Path $repoRoot 'out'
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    $OutputPath = Join-Path $outDir 'participant-users.csv'
}

function New-WorkshopPassword {
    param([int]$Length = 20)

    $upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
    $lower = 'abcdefghijkmnopqrstuvwxyz'
    $digits = '23456789'
    $symbols = '!#$%*-_=+?'
    $allCharacters = ($upper + $lower + $digits + $symbols).ToCharArray()

    $requiredCharacters = @(
        $upper[(Get-Random -Minimum 0 -Maximum $upper.Length)]
        $lower[(Get-Random -Minimum 0 -Maximum $lower.Length)]
        $digits[(Get-Random -Minimum 0 -Maximum $digits.Length)]
        $symbols[(Get-Random -Minimum 0 -Maximum $symbols.Length)]
    )

    $remainingCharacters = for ($index = $requiredCharacters.Count; $index -lt $Length; $index++) {
        $allCharacters[(Get-Random -Minimum 0 -Maximum $allCharacters.Length)]
    }

    -join (($requiredCharacters + $remainingCharacters) | Sort-Object { Get-Random })
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

function Grant-OwnerOnResourceGroup {
    param(
        [string]$ObjectId,
        [string]$ResourceGroup
    )

    $scope = az group show --name $ResourceGroup --query id -o tsv 2>$null
    if (-not $scope) {
        Write-Host "Creating resource group $ResourceGroup in $Location" -ForegroundColor Yellow
        az group create --name $ResourceGroup --location $Location --tags workshop=foundry-workshop | Out-Null
        $scope = az group show --name $ResourceGroup --query id -o tsv
    }

    $assignment = az role assignment create `
        --assignee-object-id $ObjectId `
        --assignee-principal-type User `
        --role Owner `
        --scope $scope 2>&1

    if ($LASTEXITCODE -ne 0 -and ($assignment -notmatch 'RoleAssignmentExists')) {
        throw ($assignment | Out-String)
    }
}

$forceChangePasswordText = if ($ForceChangePasswordNextSignIn.IsPresent) { 'true' } else { 'false' }
$records = @()

if (-not $UserDomain) {
    $UserDomain = Resolve-DefaultUserDomain
    Write-Host "Using tenant domain $UserDomain for participant users" -ForegroundColor Cyan
}

for ($participantNumber = 1; $participantNumber -le $Count; $participantNumber++) {
    $suffix = '{0:D2}' -f $participantNumber
    $userPrincipalName = "$UserPrefix-$suffix@$UserDomain"
    $displayName = "Foundry Workshop Participant $suffix"
    $resourceGroup = "$ResourceGroupPrefix-$suffix"
    $password = New-WorkshopPassword

    Write-Host "[$suffix] $userPrincipalName -> $resourceGroup" -ForegroundColor Cyan

    $objectId = az ad user show --id $userPrincipalName --query id -o tsv 2>$null
    $passwordForRecord = $password

    if ($objectId) {
        Write-Host "  user exists" -ForegroundColor Yellow
        if ($ResetExistingPasswords.IsPresent) {
            Invoke-AzCliJson -Arguments @(
                'ad', 'user', 'update',
                '--id', $userPrincipalName,
                '--password', $password,
                '--force-change-password-next-sign-in', $forceChangePasswordText
            ) | Out-Null
        } else {
            $passwordForRecord = '<unchanged>'
        }
    } else {
        $objectId = Invoke-AzCliJson -Arguments @(
            'ad', 'user', 'create',
            '--display-name', $displayName,
            '--user-principal-name', $userPrincipalName,
            '--password', $password,
            '--force-change-password-next-sign-in', $forceChangePasswordText,
            '--query', 'id',
            '-o', 'tsv'
        )
    }

    Grant-OwnerOnResourceGroup -ObjectId $objectId -ResourceGroup $resourceGroup

    if ($MfaExclusionGroupId) {
        $groupAddOutput = az ad group member add --group $MfaExclusionGroupId --member-id $objectId 2>&1
        if ($LASTEXITCODE -ne 0 -and ($groupAddOutput -notmatch 'already exist|already exists|One or more added object references already exist')) {
            throw ($groupAddOutput | Out-String)
        }
    }

    $records += [pscustomobject]@{
        Number = $suffix
        UserPrincipalName = $userPrincipalName
        Password = $passwordForRecord
        ResourceGroup = $resourceGroup
        ObjectId = $objectId
    }
}

$records | Export-Csv -Path $OutputPath -NoTypeInformation

Write-Host ""
Write-Host "Participant user list written to $OutputPath" -ForegroundColor Green
Write-Host "Store this file securely; it contains initial passwords for newly created or reset users." -ForegroundColor Yellow