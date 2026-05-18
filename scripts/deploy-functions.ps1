<#
.SYNOPSIS
  Deploy the Functions app code using azd or func core tools.
#>
[CmdletBinding()]
param(
    [switch]$UseFunc
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path "$PSScriptRoot/.."
Push-Location $repoRoot
try {
    if ($UseFunc) {
        $functionAppName = (& azd env get-value AZURE_FUNCTION_APP_NAME).Trim()
        if (-not $functionAppName) { throw "AZURE_FUNCTION_APP_NAME not set in azd env." }
        Push-Location (Join-Path $repoRoot "src/functions")
        try {
            & func azure functionapp publish $functionAppName --python
        } finally { Pop-Location }
    } else {
        & azd deploy functions
    }
} finally {
    Pop-Location
}
