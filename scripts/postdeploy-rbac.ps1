# Assign every RG-scoped role a workshop participant needs, for one or more
# principals (UPN or objectId). Idempotent — safe to re-run.
#
# Usage (PowerShell):
#   # Common case — assigns to *you* (the az-logged-in user). Only the RG is required.
#   ./scripts/postdeploy-rbac.ps1 -ResourceGroup rg-foundry-alice
#
#   # Multi-principal:
#   ./scripts/postdeploy-rbac.ps1 -ResourceGroup rg-foundry-alice `
#                                 -Principals alice@contoso.com,bob@contoso.com `
#                                 [-Subscription <sub-id>]
#
# Roles granted (each scoped to its resource in the RG):
#   * Cognitive Services User              on the Foundry account
#   * Cognitive Services OpenAI User       on the Foundry account
#   * Azure AI User                        on the Foundry account  (req. for Voice Live)
#   * Search Index Data Contributor        on AI Search
#   * Search Service Contributor           on AI Search
#   * Storage Blob Data Contributor        on Storage
#   * Storage Queue Data Contributor       on Storage
#   * Monitoring Metrics Publisher         on App Insights
# Re-runs safely — Azure deduplicates role assignments by (principal, role, scope).

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ResourceGroup,
    [string[]]$Principals,
    [string]$Subscription
)

$ErrorActionPreference = 'Stop'

if ($Subscription) {
    az account set --subscription $Subscription | Out-Null
}

if (-not $Principals -or $Principals.Count -eq 0) {
    $me = az ad signed-in-user show --query "userPrincipalName" -o tsv
    if (-not $me) {
        throw "No -Principals supplied and could not resolve the signed-in user. Run 'az login' first."
    }
    Write-Host "No -Principals supplied; defaulting to signed-in user: $me"
    $Principals = @($me)
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
    if (-not $Scope) {
        Write-Warning "  skip '$Role' — scope not resolved"
        return
    }
    $scopeLeaf = $Scope.Split('/')[-1]
    Write-Host "  grant '$Role' on $scopeLeaf to $Oid"
    $out = az role assignment create --assignee-object-id $Oid --assignee-principal-type User `
        --role $Role --scope $Scope 2>&1
    if ($LASTEXITCODE -ne 0) {
        # Retry without principal-type in case the principal is a service principal.
        $out = az role assignment create --assignee $Oid --role $Role --scope $Scope 2>&1
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "    FAILED: $out"
    }
}

foreach ($p in $Principals) {
    Write-Host "Resolving $p"
    $oid = Resolve-Principal -IdOrUpn $p
    Write-Host "  -> objectId $oid"

    Grant -Oid $oid -Role 'Cognitive Services User'           -Scope $foundry
    Grant -Oid $oid -Role 'Cognitive Services OpenAI User'    -Scope $foundry
    Grant -Oid $oid -Role 'Azure AI User'                     -Scope $foundry
    Grant -Oid $oid -Role 'Search Index Data Contributor'     -Scope $search
    Grant -Oid $oid -Role 'Search Service Contributor'        -Scope $search
    Grant -Oid $oid -Role 'Storage Blob Data Contributor'     -Scope $storage
    Grant -Oid $oid -Role 'Storage Queue Data Contributor'    -Scope $storage
    Grant -Oid $oid -Role 'Monitoring Metrics Publisher'      -Scope $appi
}

Write-Host ""
Write-Host "Done. RBAC propagation can take a few minutes."
