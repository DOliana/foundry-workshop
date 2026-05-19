# Assign every RG-scoped role a workshop participant needs, for one or more
# principals (UPN or objectId). Idempotent — safe to re-run.
#
# Usage (PowerShell):
#   ./scripts/postdeploy-rbac.ps1 -ResourceGroup rg-foundry-alice `
#                                 -Principals alice@contoso.com,bob@contoso.com `
#                                 [-Subscription <sub-id>]
#
# Roles granted (each scoped to its resource in the RG):
#   * Cognitive Services User              on the Foundry account
#   * Cognitive Services OpenAI User       on the Foundry account
#   * Search Index Data Contributor        on AI Search
#   * Search Service Contributor           on AI Search
#   * Storage Blob Data Contributor        on Storage
#   * Storage Queue Data Contributor       on Storage
#   * Monitoring Metrics Publisher         on App Insights
# Re-runs safely — Azure deduplicates role assignments by (principal, role, scope).

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ResourceGroup,
    [Parameter(Mandatory = $true)][string[]]$Principals,
    [string]$Subscription
)

$ErrorActionPreference = 'Stop'

if ($Subscription) {
    az account set --subscription $Subscription | Out-Null
}

# Look up resource ids by listing the RG
$foundry = az resource list -g $ResourceGroup --resource-type Microsoft.CognitiveServices/accounts --query "[?kind=='AIServices'] | [0].id" -o tsv
$search  = az resource list -g $ResourceGroup --resource-type Microsoft.Search/searchServices --query "[0].id" -o tsv
$storage = az resource list -g $ResourceGroup --resource-type Microsoft.Storage/storageAccounts --query "[0].id" -o tsv
$appi    = az resource list -g $ResourceGroup --resource-type Microsoft.Insights/components --query "[0].id" -o tsv

if (-not $foundry) { Write-Warning "No Foundry account found in $ResourceGroup" }
if (-not $search)  { Write-Warning "No AI Search service found in $ResourceGroup" }
if (-not $storage) { Write-Warning "No Storage account found in $ResourceGroup" }
if (-not $appi)    { Write-Warning "No Application Insights resource found in $ResourceGroup" }

function Resolve-Principal {
    param([string]$IdOrUpn)
    # If it looks like a GUID, treat as objectId. Otherwise look up by UPN.
    if ($IdOrUpn -match '^[0-9a-fA-F-]{36}$') { return $IdOrUpn }
    $oid = az ad user show --id $IdOrUpn --query id -o tsv 2>$null
    if (-not $oid) {
        $oid = az ad sp show --id $IdOrUpn --query id -o tsv 2>$null
    }
    if (-not $oid) { throw "Could not resolve principal '$IdOrUpn'" }
    return $oid
}

function Grant {
    param([string]$Oid, [string]$Role, [string]$Scope)
    if (-not $Scope) { return }
    Write-Host "  grant '$Role' on $($Scope.Split('/')[-1]) to $Oid"
    az role assignment create --assignee-object-id $Oid --assignee-principal-type User `
        --role $Role --scope $Scope 2>&1 | Out-Null
    # If user-type fails (e.g. it's a service principal), retry without -principal-type
    if ($LASTEXITCODE -ne 0) {
        az role assignment create --assignee $Oid --role $Role --scope $Scope 2>&1 | Out-Null
    }
}

foreach ($p in $Principals) {
    Write-Host "Resolving $p"
    $oid = Resolve-Principal -IdOrUpn $p
    Write-Host "  -> objectId $oid"

    Grant -Oid $oid -Role 'Cognitive Services User'           -Scope $foundry
    Grant -Oid $oid -Role 'Cognitive Services OpenAI User'    -Scope $foundry
    Grant -Oid $oid -Role 'Search Index Data Contributor'     -Scope $search
    Grant -Oid $oid -Role 'Search Service Contributor'        -Scope $search
    Grant -Oid $oid -Role 'Storage Blob Data Contributor'     -Scope $storage
    Grant -Oid $oid -Role 'Storage Queue Data Contributor'    -Scope $storage
    Grant -Oid $oid -Role 'Monitoring Metrics Publisher'      -Scope $appi
}

Write-Host ""
Write-Host "Done. RBAC propagation can take a few minutes."
