#!/usr/bin/env bash
set -euo pipefail

# Rsync this repo to the deployed GPU VM.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVFILE="$ROOT_DIR/.demo/outputs.env"

if [[ ! -f "$ENVFILE" ]]; then
  echo "ERROR: $ENVFILE not found. Run 'make deploy' first." >&2
  exit 2
fi
source "$ENVFILE"

VM_IP="${vmPublicIp:-}"
USER="${adminUsername:-$(whoami)}"
if [[ -z "$VM_IP" ]]; then
  echo "ERROR: vmPublicIp not found in outputs." >&2
  exit 2
fi

echo "[push] Syncing repo to ${USER}@${VM_IP}:/opt/anf-nim-demo ..."
rsync -avz --delete \
  --exclude '.demo' \
  --exclude '.git' \
  --exclude '.env' \
  --exclude '__pycache__' \
  --exclude 'seed research' \
  -e "ssh -o StrictHostKeyChecking=no" \
  "$ROOT_DIR/" "${USER}@${VM_IP}:/opt/anf-nim-demo/"

echo "✅ Repo synced to VM."
