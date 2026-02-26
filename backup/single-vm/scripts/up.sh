#!/usr/bin/env bash
set -euo pipefail

# Start the demo on the VM (runs ops/run_demo.sh remotely).
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVFILE="$ROOT_DIR/.demo/outputs.env"

if [[ ! -f "$ENVFILE" ]]; then
  echo "ERROR: $ENVFILE not found. Run 'make deploy' first." >&2
  exit 2
fi
source "$ENVFILE"

VM_IP="${vmPublicIp:-}"
USER="${adminUsername:-$(whoami)}"
NGC_KEY="${NGC_API_KEY:-}"
ANF_IP="${anfMountIp:-}"
ANF_EXPORT="${anfExportPath:-}"

if [[ -z "$VM_IP" ]]; then echo "ERROR: vmPublicIp missing." >&2; exit 2; fi
if [[ -z "$NGC_KEY" ]]; then echo "ERROR: NGC_API_KEY is required." >&2; exit 2; fi
if [[ -z "$ANF_IP" ]]; then echo "ERROR: anfMountIp missing." >&2; exit 2; fi

echo "[up] Starting demo on ${USER}@${VM_IP} ..."
ssh -o StrictHostKeyChecking=no "${USER}@${VM_IP}" \
  "sudo NGC_API_KEY='${NGC_KEY}' ANF_MOUNT_IP='${ANF_IP}' ANF_EXPORT_PATH='${ANF_EXPORT}' bash /opt/anf-nim-demo/ops/run_demo.sh"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  🎉 AlphaAgent is LIVE!                             ║"
echo "║  UI: http://${VM_IP}:8501                            ║"
echo "╚══════════════════════════════════════════════════════╝"
