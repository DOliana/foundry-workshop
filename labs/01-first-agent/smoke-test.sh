#!/usr/bin/env bash
# Lab 00 smoke test. Calls /api/log_request on the deployed Functions app and
# verifies the resulting log blob lands in the Storage account.
#
# Exercises: auth + Functions HTTP + Managed Identity + Storage write + your
# Storage Blob Data Contributor role assignment.

set -euo pipefail

# --- pretty output ---------------------------------------------------------
if [[ -t 1 ]]; then
    C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_RED=$'\033[31m'
    C_GRAY=$'\033[90m'; C_RESET=$'\033[0m'
else
    C_CYAN=""; C_GREEN=""; C_RED=""; C_GRAY=""; C_RESET=""
fi
step()  { printf "%s==> %s%s\n" "$C_CYAN"  "$*" "$C_RESET"; }
ok()    { printf "%s  OK  %s%s\n" "$C_GREEN" "$*" "$C_RESET"; }
fail()  { printf "%s  FAIL %s%s\n" "$C_RED"   "$*" "$C_RESET"; }
info()  { printf "%s      %s%s\n" "$C_GRAY"  "$*" "$C_RESET"; }

# --- read azd outputs ------------------------------------------------------
step "Reading azd environment values"
funcApp=$(azd env get-value AZURE_FUNCTION_APP_NAME)
rg=$(azd env get-value AZURE_RESOURCE_GROUP)
funcHost=$(azd env get-value AZURE_FUNCTION_APP_HOSTNAME)
storage=$(azd env get-value AZURE_STORAGE_ACCOUNT)

for kv in "AZURE_FUNCTION_APP_NAME=$funcApp" "AZURE_RESOURCE_GROUP=$rg" \
          "AZURE_FUNCTION_APP_HOSTNAME=$funcHost" "AZURE_STORAGE_ACCOUNT=$storage"; do
    name="${kv%%=*}"; value="${kv#*=}"
    if [[ -z "$value" ]]; then
        fail "$name is empty. Did 'azd up' finish?"
        exit 1
    fi
    info "$name = $value"
done
ok "azd outputs resolved"

# --- function key ----------------------------------------------------------
step "Fetching Functions master key"
funcKey=$(az functionapp keys list --name "$funcApp" --resource-group "$rg" --query masterKey -o tsv)
if [[ -z "$funcKey" ]]; then
    fail "Could not retrieve master key. Are you signed in (az login) and on the right subscription?"
    exit 1
fi
ok "Master key retrieved (length=${#funcKey})"

# --- conversation id (no uuidgen dependency) -------------------------------
if [[ -r /proc/sys/kernel/random/uuid ]]; then
    convId="setup-$(cat /proc/sys/kernel/random/uuid)"
else
    convId="setup-$(python3 -c 'import uuid;print(uuid.uuid4())')"
fi

# --- call Functions --------------------------------------------------------
uri="https://$funcHost/api/log_request?code=$funcKey"
step "POST $uri"
info "conversation_id = $convId"

httpResp=$(mktemp)
status=$(curl -sS -o "$httpResp" -w "%{http_code}" \
    -X POST "$uri" \
    -H "content-type: application/json" \
    -d "{\"conversation_id\": \"$convId\", \"channel\": \"chat\"}")

if [[ "$status" != "200" && "$status" != "201" ]]; then
    fail "HTTP $status. Body:"
    cat "$httpResp"; echo
    exit 1
fi

logBlob=$(python3 -c "import json,sys;print(json.load(open('$httpResp')).get('log_blob',''))")
if [[ -z "$logBlob" ]]; then
    fail "Response did not contain a 'log_blob' field. Body:"
    cat "$httpResp"; echo
    exit 1
fi
ok "Functions responded (HTTP $status)"
info "log_blob = $logBlob"

# --- list the blob ---------------------------------------------------------
step "Listing blobs in 'logs' container for conversation_id"
blobs=$(az storage blob list \
    --account-name "$storage" \
    --container-name logs \
    --auth-mode login \
    --query "[?contains(name, '$convId')].name" -o tsv)

if [[ -z "$blobs" ]]; then
    fail "No blob found for $convId. Likely causes: missing 'Storage Blob Data Contributor' role on $storage, or the Function didn't write yet. Re-run 'azd provision' to re-apply RBAC, then retry."
    exit 1
fi
while IFS= read -r b; do [[ -n "$b" ]] && info "$b"; done <<<"$blobs"
ok "Blob found in Storage"

echo
printf "%sSMOKE TEST PASSED%s\n" "$C_GREEN" "$C_RESET"
echo "  conversation_id: $convId"
echo "  blob path:       $logBlob"
echo
printf "%sInspect the blob with:%s\n" "$C_GRAY" "$C_RESET"
echo "  az storage blob download --account-name $storage --container-name logs --name \"$logBlob\" --file ./log.json --auth-mode login"
