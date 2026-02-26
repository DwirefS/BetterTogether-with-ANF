#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# AlphaAgent — VM-Side Demo Bootstrap
# ============================================================================
# Runs ON the GPU VM (called remotely by scripts/up.sh).
# Mounts ANF, authenticates NGC, and starts Docker Compose services.
# ============================================================================

# Expected env vars
: "${NGC_API_KEY:?NGC_API_KEY is required}"
: "${ANF_MOUNT_IP:?ANF_MOUNT_IP is required}"
: "${ANF_EXPORT_PATH:?ANF_EXPORT_PATH is required}"

REPO_DIR="/opt/anf-nim-demo"
COMPOSE_DIR="$REPO_DIR/compose"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  AlphaAgent — VM Bootstrap (Better Together Demo)       ║"
echo "╚══════════════════════════════════════════════════════════╝"

echo "[1/7] Validating GPU driver (waiting for NVIDIA GPU driver extension)..."
for i in {1..120}; do
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    echo "  ✅ GPU ready."
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    break
  fi
  sleep 10
  if [[ "$i" -eq 120 ]]; then
    echo "  ❌ nvidia-smi not ready after 20 minutes." >&2
    echo "  Check: /var/log/azure/nvidia-vmext-status" >&2
    exit 1
  fi
done

echo "[2/7] Mounting Azure NetApp Files NFS volume..."
mkdir -p /mnt/anf
if mountpoint -q /mnt/anf; then
  echo "  ✅ ANF already mounted."
else
  apt-get update -qq >/dev/null 2>&1
  apt-get install -y -qq nfs-common >/dev/null 2>&1
  mount -t nfs -o vers=4.1 "${ANF_MOUNT_IP}:/${ANF_EXPORT_PATH}" /mnt/anf
  # Persist across reboots
  grep -q "/mnt/anf" /etc/fstab || \
    echo "${ANF_MOUNT_IP}:/${ANF_EXPORT_PATH} /mnt/anf nfs4 defaults,vers=4.1,minorversion=1 0 0" >> /etc/fstab
  echo "  ✅ Mounted ANF to /mnt/anf"
fi

echo "[3/7] Authenticating to NVIDIA NGC container registry..."
echo "${NGC_API_KEY}" | docker login nvcr.io -u '$oauthtoken' --password-stdin >/dev/null 2>&1
echo "  ✅ NGC authenticated."

echo "[4/7] Writing Docker Compose environment..."
mkdir -p "$COMPOSE_DIR"
cat > "$COMPOSE_DIR/.env" <<EOF
NGC_API_KEY=${NGC_API_KEY}
LOCAL_NIM_CACHE=/var/lib/nim-cache
DATA_ROOT=/mnt/anf/data
INDEX_ROOT=/mnt/anf/index
EOF
mkdir -p /var/lib/nim-cache
mkdir -p /mnt/anf/data /mnt/anf/index
echo "  ✅ Environment configured."

echo "[5/7] Pulling NIM container images (this may take several minutes on first run)..."
cd "$COMPOSE_DIR"
docker compose pull
echo "  ✅ Images pulled."

echo "[6/7] Starting NVIDIA NIM microservices (LLM + Embeddings)..."
docker compose up -d nim-llm nim-embed
echo "  ⏳ NIM services starting (model optimization on first boot takes 5-10 minutes)..."

echo "[7/7] Running init (synthetic data + index) and starting UI..."
docker compose run --rm init
docker compose up -d ui

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ AlphaAgent Demo is LIVE!                            ║"
echo "║                                                          ║"
echo "║  Streamlit UI: http://$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'):8501  ║"
echo "║                                                          ║"
echo "║  ANF Data:  /mnt/anf/data   (synthetic FSI documents)   ║"
echo "║  ANF Index: /mnt/anf/index  (embedding index)            ║"
echo "╚══════════════════════════════════════════════════════════╝"
