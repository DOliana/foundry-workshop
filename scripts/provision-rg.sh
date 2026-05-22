#!/usr/bin/env bash
# Provision the workshop infrastructure into an existing (or to-be-created)
# resource group. Idempotent — safe to re-run.
#
# Usage:
#   ./scripts/provision-rg.sh \
#       --rg rg-foundry-alice \
#       [--location swedencentral] \
#       [--env-name foundry-alice] \
#       [--subscription <sub-id>] \
#       [--principal <object-id>]
#
# Short aliases:
#   -g == --rg
#   -l == --location
#
# What it does:
#   1. Ensures the RG exists (creates it if not).
#   2. Initialises or reuses the azd environment $ENV_NAME.
#   3. Sets AZURE_LOCATION + AZURE_RESOURCE_GROUP in the azd env so azd
#      deploys into the existing RG instead of creating a new one.
#   4. Runs `azd provision`.
#
# If azd does not deploy into the existing RG correctly, fall back to:
#   az deployment group create \
#       --resource-group "$RG" \
#       --template-file infra/main.bicep \
#       --parameters infra/main.parameters.json \
#       --parameters environmentName=$ENV_NAME principalId=$PRINCIPAL_ID

set -euo pipefail

RG=""
LOCATION="swedencentral"
ENV_NAME=""
SUB=""
PRINCIPAL_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rg|-g) RG="$2"; shift 2 ;;
    --location|-l) LOCATION="$2"; shift 2 ;;
    --env-name) ENV_NAME="$2"; shift 2 ;;
    --subscription) SUB="$2"; shift 2 ;;
    --principal) PRINCIPAL_ID="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: ./scripts/provision-rg.sh --rg|-g <name> [--location|-l <region>] [--env-name <env>] [--subscription <sub>] [--principal <oid>]"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$RG" ]]; then
  echo "Usage: ./scripts/provision-rg.sh --rg|-g <name> [--location|-l <region>] [--env-name <env>] [--subscription <sub>] [--principal <oid>]" >&2
  exit 1
fi

if [[ -z "$ENV_NAME" ]]; then ENV_NAME="$RG"; fi

if [[ -n "$SUB" ]]; then
  echo "Selecting subscription $SUB"
  az account set --subscription "$SUB"
fi

if [[ "$(az group exists --name "$RG")" != "true" ]]; then
  echo "Creating resource group $RG in $LOCATION"
  az group create --name "$RG" --location "$LOCATION" --tags workshop=foundry-workshop >/dev/null
else
  echo "Resource group $RG already exists"
fi

# Move to repo root (parent of scripts/)
cd "$(dirname "$0")/.."

# Initialise or refresh azd environment
have_env=false
if azd env list --output json 2>/dev/null | grep -q "\"Name\": \"$ENV_NAME\""; then
  have_env=true
fi
if [[ "$have_env" == "false" ]]; then
  echo "Creating azd environment $ENV_NAME"
  azd env new "$ENV_NAME" --location "$LOCATION"
else
  echo "Reusing azd environment $ENV_NAME"
  azd env select "$ENV_NAME"
fi

azd env set AZURE_LOCATION "$LOCATION"
azd env set AZURE_RESOURCE_GROUP "$RG"

if [[ -n "$PRINCIPAL_ID" ]]; then
  azd env set AZURE_PRINCIPAL_ID "$PRINCIPAL_ID"
fi

echo "Running azd provision against $RG"
if ! azd provision; then
  echo ""
  echo "azd provision failed. Fallback: run the bicep directly."
  echo "  az deployment group create -g $RG \\"
  echo "      --template-file infra/main.bicep \\"
  echo "      --parameters infra/main.parameters.json \\"
  echo "      --parameters environmentName=$ENV_NAME"
  exit 1
fi

echo ""
echo "Provisioning complete."
echo "Next step: ./scripts/postdeploy-rbac.sh --rg $RG --principal <upn-or-oid> [--principal <upn-or-oid> ...]"
