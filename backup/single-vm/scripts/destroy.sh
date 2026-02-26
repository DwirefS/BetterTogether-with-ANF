#!/usr/bin/env bash
set -euo pipefail

# Destroy the demo resource group. DANGEROUS — deletes everything!
RG="${1:-}"

if [[ -z "$RG" ]]; then
  echo "Usage: destroy.sh <resource-group>" >&2
  exit 2
fi

echo "⚠️  WARNING: This will permanently delete resource group '$RG' and ALL resources inside it."
echo ""
read -p "Type the resource group name to confirm: " CONFIRM

if [[ "$CONFIRM" != "$RG" ]]; then
  echo "Aborted. Names did not match."
  exit 1
fi

echo "Deleting resource group '$RG' ..."
az group delete -n "$RG" --yes --no-wait
echo "✅ Deletion initiated (runs in background)."
echo "   Monitor: az group show -n $RG --query properties.provisioningState -o tsv"
