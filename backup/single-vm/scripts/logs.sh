#!/usr/bin/env bash
set -euo pipefail

# Tail Streamlit UI logs on the VM.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVFILE="$ROOT_DIR/.demo/outputs.env"

if [[ ! -f "$ENVFILE" ]]; then
  echo "ERROR: $ENVFILE not found. Run 'make deploy' first." >&2
  exit 2
fi
source "$ENVFILE"

VM_IP="${vmPublicIp:-}"
USER="${adminUsername:-$(whoami)}"

if [[ -z "$VM_IP" ]]; then echo "ERROR: vmPublicIp missing." >&2; exit 2; fi

echo "Tailing logs on ${VM_IP} ..."
ssh -o StrictHostKeyChecking=no "${USER}@${VM_IP}" \
  "cd /opt/anf-nim-demo/compose && sudo docker compose logs -f ui"
