#!/usr/bin/env bash
set -euo pipefail

# Show demo status and key URLs.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVFILE="$ROOT_DIR/.demo/outputs.env"

if [[ ! -f "$ENVFILE" ]]; then
  echo "No deployment found. Run 'make deploy' first." >&2
  exit 2
fi
source "$ENVFILE"

VM_IP="${vmPublicIp:-unknown}"
VM_FQDN="${vmFqdn:-unknown}"
ANF_IP="${anfMountIp:-unknown}"
ANF_EXPORT="${anfExportPath:-unknown}"

echo "╔═══════════════════════════════════════════════════════╗"
echo "║  AlphaAgent Demo Status                              ║"
echo "╠═══════════════════════════════════════════════════════╣"
echo "║  VM Public IP:    ${VM_IP}"
echo "║  VM FQDN:         ${VM_FQDN}"
echo "║  ANF Mount:       ${ANF_IP}:/${ANF_EXPORT}"
echo "║  Streamlit UI:    http://${VM_IP}:8501"
echo "╚═══════════════════════════════════════════════════════╝"

# Try to check container status
echo ""
echo "Container status (via SSH):"
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
  "${adminUsername:-$(whoami)}@${VM_IP}" \
  "cd /opt/anf-nim-demo/compose && sudo docker compose ps" 2>/dev/null || echo "  (unable to connect)"
