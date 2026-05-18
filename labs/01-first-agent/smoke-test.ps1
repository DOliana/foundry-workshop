<#
.SYNOPSIS
  Lab 00 smoke test. Calls /api/log_request on the deployed Functions app and
  verifies the resulting log blob lands in the Storage account.

  Exercises: auth + Functions HTTP + Managed Identity + Storage write + your
  Storage Blob Data Contributor role assignment.

.EXAMPLE
  ./labs/01-first-agent/smoke-test.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Write-Step($msg)    { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)      { Write-Host "  OK  $msg" -ForegroundColor Green }
function Write-Fail($msg)    { Write-Host "  FAIL $msg" -ForegroundColor Red }
function Write-Info($msg)    { Write-Host "      $msg" -ForegroundColor Gray }

Write-Step "Reading azd environment values"
$funcApp  = (azd env get-value AZURE_FUNCTION_APP_NAME).Trim()
$rg       = (azd env get-value AZURE_RESOURCE_GROUP).Trim()
$funcHost = (azd env get-value AZURE_FUNCTION_APP_HOSTNAME).Trim()
$storage  = (azd env get-value AZURE_STORAGE_ACCOUNT).Trim()

foreach ($pair in @(
    @{ Name = "AZURE_FUNCTION_APP_NAME";     Value = $funcApp  },
    @{ Name = "AZURE_RESOURCE_GROUP";        Value = $rg       },
    @{ Name = "AZURE_FUNCTION_APP_HOSTNAME"; Value = $funcHost },
    @{ Name = "AZURE_STORAGE_ACCOUNT";       Value = $storage  }
)) {
    if (-not $pair.Value) {
        Write-Fail "$($pair.Name) is empty. Did 'azd up' finish?"
        exit 1
    }
    Write-Info "$($pair.Name) = $($pair.Value)"
}
Write-Ok "azd outputs resolved"

Write-Step "Fetching Functions master key"
$funcKey = az functionapp keys list --name $funcApp --resource-group $rg --query masterKey -o tsv
if (-not $funcKey) {
    Write-Fail "Could not retrieve master key. Are you signed in (az login) and on the right subscription?"
    exit 1
}
Write-Ok "Master key retrieved (length=$($funcKey.Length))"

$convId = "setup-$([guid]::NewGuid())"
$uri    = "https://$funcHost/api/log_request?code=$funcKey"
$body   = @{ conversation_id = $convId; channel = "chat" } | ConvertTo-Json

Write-Step "POST $uri"
Write-Info "conversation_id = $convId"
try {
    $resp = Invoke-RestMethod -Uri $uri -Method POST -ContentType "application/json" -Body $body
} catch {
    Write-Fail "HTTP call failed: $($_.Exception.Message)"
    exit 1
}

if (-not $resp.log_blob) {
    Write-Fail "Response did not contain a 'log_blob' field. Got: $($resp | ConvertTo-Json -Compress)"
    exit 1
}
Write-Ok "Functions responded"
Write-Info "log_blob = $($resp.log_blob)"

Write-Step "Listing blobs in 'logs' container for conversation_id"
$blobs = az storage blob list `
    --account-name $storage `
    --container-name logs `
    --auth-mode login `
    --query "[?contains(name, '$convId')].name" -o tsv

if (-not $blobs) {
    Write-Fail "No blob found for $convId. Likely causes: missing 'Storage Blob Data Contributor' role on $storage, or the Function didn't write yet. Re-run 'azd provision' to re-apply RBAC, then retry."
    exit 1
}
foreach ($b in $blobs -split "`n") { if ($b) { Write-Info $b } }
Write-Ok "Blob found in Storage"

Write-Host ""
Write-Host "SMOKE TEST PASSED" -ForegroundColor Green
Write-Host "  conversation_id: $convId"
Write-Host "  blob path:       $($resp.log_blob)"
Write-Host ""
Write-Host "Inspect the blob with:" -ForegroundColor Gray
Write-Host "  az storage blob download --account-name $storage --container-name logs --name `"$($resp.log_blob)`" --file ./log.json --auth-mode login" -ForegroundColor Gray
