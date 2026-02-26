#!/usr/bin/env bash
set -euo pipefail

# Deploy Azure infrastructure via Bicep.
# Usage: deploy.sh <resource-group> <location> <prefix> <vm-size>

RG="${1:-}"
LOCATION="${2:-}"
PREFIX="${3:-}"
VM_SIZE="${4:-}"

if [[ -z "$RG" || -z "$LOCATION" || -z "$PREFIX" || -z "$VM_SIZE" ]]; then
  echo "Usage: deploy.sh <rg> <location> <prefix> <vm_size>" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTDIR="$ROOT_DIR/.demo"
mkdir -p "$OUTDIR"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  AlphaAgent — Azure Infrastructure Deployment           ║"
echo "║  Azure + NVIDIA + Azure NetApp Files — Better Together  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

echo "[1/6] Registering Azure resource providers (idempotent)..."
az provider register -n Microsoft.NetApp   >/dev/null 2>&1 &
az provider register -n Microsoft.Compute  >/dev/null 2>&1 &
az provider register -n Microsoft.Network  >/dev/null 2>&1 &
wait
echo "  ✅ Providers registered."

echo "[2/6] Creating resource group: $RG ($LOCATION)"
az group create -n "$RG" -l "$LOCATION" >/dev/null
echo "  ✅ Resource group ready."

# SSH key detection
PUBKEY="${SSH_PUBLIC_KEY:-}"
if [[ -z "$PUBKEY" ]]; then
  if [[ -f "$HOME/.ssh/id_ed25519.pub" ]]; then
    PUBKEY="$(cat "$HOME/.ssh/id_ed25519.pub")"
  elif [[ -f "$HOME/.ssh/id_rsa.pub" ]]; then
    PUBKEY="$(cat "$HOME/.ssh/id_rsa.pub")"
  else
    echo "  No SSH public key found. Creating ~/.ssh/id_ed25519 ..." >&2
    ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519" -N "" >/dev/null
    PUBKEY="$(cat "$HOME/.ssh/id_ed25519.pub")"
  fi
fi

DEPLOY_NAME="${PREFIX}-$(date +%Y%m%d%H%M%S)"

echo "[3/6] Deploying Bicep template (VNet + ANF + GPU VM)..."
echo "  ⏳ This takes 10-20 minutes (GPU VM + ANF provisioning)..."
az deployment group create \
  -g "$RG" \
  -n "$DEPLOY_NAME" \
  -f "$ROOT_DIR/infra/main.bicep" \
  -p prefix="$PREFIX" location="$LOCATION" adminUsername="$(whoami)" sshPublicKey="$PUBKEY" vmSize="$VM_SIZE" \
  1>/dev/null
echo "  ✅ Bicep deployment complete."

echo "[4/6] Capturing deployment outputs..."
az deployment group show -g "$RG" -n "$DEPLOY_NAME" --query properties.outputs -o json > "$OUTDIR/outputs.json"

# Convert outputs.json → outputs.env
python3 - <<'PY'
import json, pathlib
p = pathlib.Path(".demo/outputs.json")
o = json.loads(p.read_text())
lines = []
for k, v in o.items():
    val = v.get("value")
    if isinstance(val, (dict, list)):
        continue
    sval = str(val).replace('"', '\\"')
    lines.append(f'{k}="{sval}"')
pathlib.Path(".demo/outputs.env").write_text("\n".join(lines) + "\n")
print("  Wrote .demo/outputs.env")
PY

echo "[5/6] Deployment outputs:"
cat "$OUTDIR/outputs.env"

echo ""
echo "[6/6] ✅ Infrastructure ready."
echo "  Next: make push && make up NGC_API_KEY=..."
