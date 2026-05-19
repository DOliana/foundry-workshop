#!/usr/bin/env bash
# Assign every RG-scoped role a workshop participant needs, for one or more
# principals (UPN or objectId). Idempotent — safe to re-run.
#
# Usage:
#   ./scripts/postdeploy-rbac.sh \
#       --rg rg-foundry-alice \
#       --principal alice@contoso.com \
#       [--principal bob@contoso.com] \
#       [--subscription <sub-id>]
#
# Roles granted (each scoped to its resource in the RG):
#   * Cognitive Services User              on the Foundry account
#   * Cognitive Services OpenAI User       on the Foundry account
#   * Search Index Data Contributor        on AI Search
#   * Search Service Contributor           on AI Search
#   * Storage Blob Data Contributor        on Storage
#   * Storage Queue Data Contributor       on Storage
#   * Monitoring Metrics Publisher         on App Insights

set -euo pipefail

RG=""
SUB=""
PRINCIPALS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rg) RG="$2"; shift 2 ;;
    --subscription) SUB="$2"; shift 2 ;;
    --principal) PRINCIPALS+=("$2"); shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$RG" || ${#PRINCIPALS[@]} -eq 0 ]]; then
  echo "Usage: ./scripts/postdeploy-rbac.sh --rg <name> --principal <upn-or-oid> [--principal ...] [--subscription <sub>]" >&2
  exit 1
fi

if [[ -n "$SUB" ]]; then
  az account set --subscription "$SUB"
fi

FOUNDRY=$(az resource list -g "$RG" --resource-type Microsoft.CognitiveServices/accounts --query "[?kind=='AIServices'] | [0].id" -o tsv)
SEARCH=$(az resource list -g "$RG" --resource-type Microsoft.Search/searchServices --query "[0].id" -o tsv)
STORAGE=$(az resource list -g "$RG" --resource-type Microsoft.Storage/storageAccounts --query "[0].id" -o tsv)
APPI=$(az resource list -g "$RG" --resource-type Microsoft.Insights/components --query "[0].id" -o tsv)

[[ -z "$FOUNDRY" ]] && echo "WARN: no Foundry account in $RG" >&2
[[ -z "$SEARCH"  ]] && echo "WARN: no AI Search in $RG" >&2
[[ -z "$STORAGE" ]] && echo "WARN: no Storage account in $RG" >&2
[[ -z "$APPI"    ]] && echo "WARN: no App Insights in $RG" >&2

resolve_principal() {
  local v="$1"
  if [[ "$v" =~ ^[0-9a-fA-F-]{36}$ ]]; then
    echo "$v"
    return
  fi
  local oid
  oid=$(az ad user show --id "$v" --query id -o tsv 2>/dev/null || true)
  if [[ -z "$oid" ]]; then
    oid=$(az ad sp show --id "$v" --query id -o tsv 2>/dev/null || true)
  fi
  if [[ -z "$oid" ]]; then
    echo "Could not resolve principal '$v'" >&2
    return 1
  fi
  echo "$oid"
}

grant() {
  local oid="$1" role="$2" scope="$3"
  if [[ -z "$scope" ]]; then return; fi
  echo "  grant '$role' on ${scope##*/} to $oid"
  az role assignment create --assignee-object-id "$oid" --assignee-principal-type User \
      --role "$role" --scope "$scope" >/dev/null 2>&1 || \
    az role assignment create --assignee "$oid" --role "$role" --scope "$scope" >/dev/null 2>&1 || true
}

for p in "${PRINCIPALS[@]}"; do
  echo "Resolving $p"
  oid=$(resolve_principal "$p")
  echo "  -> objectId $oid"

  grant "$oid" 'Cognitive Services User'           "$FOUNDRY"
  grant "$oid" 'Cognitive Services OpenAI User'    "$FOUNDRY"
  grant "$oid" 'Search Index Data Contributor'     "$SEARCH"
  grant "$oid" 'Search Service Contributor'        "$SEARCH"
  grant "$oid" 'Storage Blob Data Contributor'     "$STORAGE"
  grant "$oid" 'Storage Queue Data Contributor'    "$STORAGE"
  grant "$oid" 'Monitoring Metrics Publisher'      "$APPI"
done

echo ""
echo "Done. RBAC propagation can take a few minutes."
