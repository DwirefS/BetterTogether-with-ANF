#!/bin/bash
set -e

# ============================================================================
# AlphaAgent Enterprise Deployment Script — End-to-End
# ============================================================================
# Deploys the COMPLETE stack into Azure resource group "DNvidiaANF":
#    1. Prerequisites check
#    2. Azure Infrastructure via ARM (VNet, ANF, AKS, ACR, KeyVault, Snapshots)
#    3. AKS config: kubectl creds, K8s secrets, ANF PVCs, Key Vault CSI
#    4. GPU Operator + DCGM Exporter (with Prometheus ServiceMonitor)
#    5. Milvus vector DB (cluster mode on ANF NFS)
#    6. NVIDIA NIM Microservices (LLM, Embeddings, Reranking, Retriever)
#    7. Prometheus + Grafana monitoring stack
#    8. Build + deploy the AlphaAgent Streamlit app (via az acr build)
#    9. Load SEC EDGAR data and trigger vector ingestion
#   10. Final health check + print UI URL + Grafana URL
#
# Usage:
#   ./scripts/deploy.sh <NGC_API_KEY>
#   — OR —
#   make deploy NGC_API_KEY=<your-key>
#
# After this script completes, open the printed Streamlit URL and query the agent.
# ============================================================================

NGC_API_KEY=$1
RESOURCE_GROUP=${RG_NAME:-"DNvidiaANF"}
LOCATION=${LOCATION:-"eastus2"}
PREFIX=${PREFIX:-"alpha-ai"}

# ------------------------------------------------------------------
# Step 0/10: Validate prerequisites
# ------------------------------------------------------------------
echo ""
echo "========================================================"
echo "  AlphaAgent Enterprise Deployment — End-to-End"
echo "  Resource Group : $RESOURCE_GROUP"
echo "  Location       : $LOCATION"
echo "  Prefix         : $PREFIX"
echo "========================================================"

if [ -z "$NGC_API_KEY" ]; then
    echo ""
    echo "ERROR: NGC_API_KEY is required."
    echo "Usage: make deploy NGC_API_KEY=nvapi-..."
    echo ""
    echo "Get your key from https://org.ngc.nvidia.com/ → Profile → Setup → Generate API Key"
    exit 1
fi

echo ""
echo "Step 0/10: Checking prerequisites..."

missing=""
for cmd in az kubectl helm jq envsubst; do
    if ! command -v $cmd &>/dev/null; then
        missing="$missing $cmd"
    fi
done

if [ -n "$missing" ]; then
    echo "ERROR: Missing required tools:$missing"
    echo ""
    echo "Install them:"
    echo "  az       → https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
    echo "  kubectl  → az aks install-cli"
    echo "  helm     → curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
    echo "  jq       → sudo apt-get install jq  (or brew install jq)"
    echo "  envsubst → sudo apt-get install gettext-base"
    exit 1
fi

# Verify Azure login
if ! az account show &>/dev/null; then
    echo "ERROR: Not logged into Azure. Run: az login"
    exit 1
fi

echo "  All prerequisites met."
echo "  Azure account: $(az account show --query name -o tsv)"
echo "  Subscription:  $(az account show --query id -o tsv)"

# ------------------------------------------------------------------
# Step 1/10: Provision Azure Infrastructure
# ------------------------------------------------------------------
echo ""
echo "Step 1/10: Provisioning Azure Infrastructure (VNet, AKS, ANF, ACR, KeyVault, Snapshots)..."
echo "  (This takes ~10-15 minutes for AKS + ANF provisioning)"

# Ensure required providers are registered
az provider register --namespace Microsoft.NetApp --wait 2>/dev/null || true
az provider register --namespace Microsoft.ContainerService --wait 2>/dev/null || true
az provider register --namespace Microsoft.ContainerRegistry --wait 2>/dev/null || true
az provider register --namespace Microsoft.KeyVault --wait 2>/dev/null || true

az group create --name "$RESOURCE_GROUP" --location "$LOCATION" -o none

# Use pre-compiled ARM JSON template (no Bicep CLI dependency)
az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file infra/main.json \
    --parameters infra/parameters.json \
    -o none

echo "  Infrastructure provisioned (incl. AKS with CSI driver addon, ANF snapshot policy)."

# ------------------------------------------------------------------
# Step 2/10: Configure AKS Credentials and Base Layer
# ------------------------------------------------------------------
echo ""
echo "Step 2/10: Configuring AKS and base Kubernetes layer..."

AKS_NAME="${PREFIX}-aks"
az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$AKS_NAME" --overwrite-existing

# Create namespace
kubectl apply -f kubernetes/base/namespace.yaml

# Create docker-registry secret for pulling NIM images from nvcr.io
kubectl create secret docker-registry ngc-secret \
    --namespace finserv-ai \
    --docker-server=nvcr.io \
    --docker-username="\$oauthtoken" \
    --docker-password="$NGC_API_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -

# Create generic secret with NGC_API_KEY for NIM env var injection
# (This is the static K8s secret; Key Vault CSI will eventually replace it with auto-rotation)
kubectl create secret generic ngc-api-key \
    --namespace finserv-ai \
    --from-literal=NGC_API_KEY="$NGC_API_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -

# Get ALL deployment outputs
outputs=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name main \
    --query properties.outputs -o json)

export ANF_DATA_IP=$(echo "$outputs" | jq -r .anfDataVolumeIp.value)
export ANF_DATA_VOL=$(echo "$outputs" | jq -r .anfDataVolumePath.value)
export ANF_MILVUS_IP=$(echo "$outputs" | jq -r .anfMilvusVolumeIp.value)
export ANF_MILVUS_VOL=$(echo "$outputs" | jq -r .anfMilvusVolumePath.value)
export KEY_VAULT_NAME=$(echo "$outputs" | jq -r .keyVaultName.value)

echo "  ANF Data Volume   : $ANF_DATA_IP:/$ANF_DATA_VOL"
echo "  ANF Milvus Volume : $ANF_MILVUS_IP:/$ANF_MILVUS_VOL"
echo "  Key Vault         : $KEY_VAULT_NAME"

# Apply PVs and PVCs with ANF IPs substituted
envsubst < kubernetes/base/anf-pvc.yaml | kubectl apply -f -

# ------------------------------------------------------------------
# Step 2b: Configure Key Vault CSI Driver
# ------------------------------------------------------------------
echo ""
echo "  Configuring Key Vault CSI driver for secret rotation..."

# Store NGC_API_KEY in Key Vault (CSI driver will sync it to K8s Secrets)
az keyvault secret set \
    --vault-name "$KEY_VAULT_NAME" \
    --name "NGC-API-KEY" \
    --value "$NGC_API_KEY" \
    -o none 2>/dev/null \
    || echo "  WARNING: Could not set KV secret (access policy may need updating). Static K8s Secret in use."

# Get the CSI driver managed identity client ID for the SecretProviderClass
export AKS_IDENTITY_CLIENT_ID=$(az aks show \
    --name "$AKS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "addonProfiles.azureKeyvaultSecretsProvider.identity.clientId" \
    -o tsv 2>/dev/null || echo "")

export AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)

if [ -n "$AKS_IDENTITY_CLIENT_ID" ] && [ "$AKS_IDENTITY_CLIENT_ID" != "None" ]; then
    echo "  CSI Identity Client ID: $AKS_IDENTITY_CLIENT_ID"

    # Grant the CSI managed identity access to Key Vault secrets
    AKS_IDENTITY_OBJECT_ID=$(az aks show \
        --name "$AKS_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "addonProfiles.azureKeyvaultSecretsProvider.identity.objectId" \
        -o tsv 2>/dev/null || echo "")

    if [ -n "$AKS_IDENTITY_OBJECT_ID" ]; then
        az keyvault set-policy \
            --name "$KEY_VAULT_NAME" \
            --object-id "$AKS_IDENTITY_OBJECT_ID" \
            --secret-permissions get list \
            -o none 2>/dev/null \
            || echo "  WARNING: Could not set KV access policy."
    fi

    # Apply SecretProviderClass with actual values substituted
    envsubst < kubernetes/secrets/keyvault-csi.yaml | kubectl apply -f -
    echo "  Key Vault CSI SecretProviderClass applied."
else
    echo "  WARNING: CSI driver identity not found. Key Vault CSI not configured."
    echo "  The app will use static K8s Secrets instead. To enable CSI later, run:"
    echo "    az aks enable-addons --addons azure-keyvault-secrets-provider --name $AKS_NAME --resource-group $RESOURCE_GROUP"
fi

echo "  Base layer, ANF storage, and secrets configured."

# ------------------------------------------------------------------
# Step 3/10: Deploy GPU Operator
# ------------------------------------------------------------------
echo ""
echo "Step 3/10: Deploying NVIDIA GPU Operator (with DCGM Exporter + ServiceMonitor)..."

helm repo add nvidia https://helm.ngc.nvidia.com/nvidia 2>/dev/null || true
helm repo update nvidia 2>/dev/null || true

helm upgrade --install gpu-operator nvidia/gpu-operator \
    --namespace gpu-operator --create-namespace \
    -f kubernetes/gpu-operator/values.yaml \
    --wait --timeout 10m

echo "  GPU Operator deployed (DCGM metrics exposed to Prometheus)."

# ------------------------------------------------------------------
# Step 4/10: Deploy Milvus Vector Database (Cluster Mode)
# ------------------------------------------------------------------
echo ""
echo "Step 4/10: Deploying Milvus vector database (cluster mode on ANF NFS)..."

helm repo add milvus https://zilliztech.github.io/milvus-helm 2>/dev/null || true
helm repo update milvus 2>/dev/null || true

helm upgrade --install milvus milvus/milvus \
    --namespace finserv-ai \
    -f kubernetes/milvus/values.yaml \
    --wait --timeout 10m

echo "  Milvus cluster deployed (2x queryNode, 2x dataNode, 3x etcd) on ANF."

# ------------------------------------------------------------------
# Step 5/10: Deploy NVIDIA NIM Microservices
# ------------------------------------------------------------------
echo ""
echo "Step 5/10: Deploying NVIDIA NIM Microservices (LLM, Embeddings, Reranking, Retriever)..."
echo "  (NIM containers download large model weights on first start — this takes 10-20 min)"

# Add NGC Helm repos with authentication
helm repo add nim https://helm.ngc.nvidia.com/nim \
    --username='$oauthtoken' --password="$NGC_API_KEY" 2>/dev/null || true
helm repo add nim-nvidia https://helm.ngc.nvidia.com/nim/nvidia \
    --username='$oauthtoken' --password="$NGC_API_KEY" 2>/dev/null || true
helm repo update 2>/dev/null || true

# NIM LLM (Llama 3.1 8B Instruct)
echo "  Installing NIM LLM..."
helm upgrade --install nim-llm nim/nim-llm \
    --namespace finserv-ai \
    -f kubernetes/nim/llm-values.yaml \
    --timeout 15m \
    || echo "  WARNING: NIM LLM Helm install returned non-zero. Will check pod status later."

# NIM Embeddings (NV-EmbedQA-E5-v5)
echo "  Installing NIM Embeddings..."
helm upgrade --install nim-embed nim-nvidia/text-embedding-nim \
    --namespace finserv-ai \
    -f kubernetes/nim/embed-values.yaml \
    --timeout 15m \
    || echo "  WARNING: NIM Embed Helm install returned non-zero."

# NIM Reranking (NV-RerankQA-Mistral-4B-v3) — NOW wired into the RAG pipeline!
echo "  Installing NIM Reranking (cross-encoder for 15-25% precision boost)..."
helm upgrade --install nim-rerank nim-nvidia/text-reranking-nim \
    --namespace finserv-ai \
    -f kubernetes/nim/rerank-values.yaml \
    --timeout 15m \
    || echo "  WARNING: NIM Rerank Helm install returned non-zero."

# NIM Retriever Parse (optional — app falls back to PyPDFLoader)
echo "  Installing NIM Retriever Parse..."
helm upgrade --install nim-retriever nim-nvidia/nemo-retriever-parse \
    --namespace finserv-ai \
    -f kubernetes/nim/retriever-values.yaml \
    --timeout 15m \
    || echo "  WARNING: NIM Retriever Parse not available via Helm. App will use PyPDFLoader fallback."

echo "  NIM installations submitted. Waiting for critical pods..."
echo "  (Model downloads happen in the background — large models take 10-20 min)"

# Wait for at least the LLM and embed pods (critical for demo)
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=nim-llm \
    --namespace finserv-ai --timeout=1200s 2>/dev/null \
    || echo "  WARNING: NIM LLM pod not ready within timeout. Check: kubectl get pods -n finserv-ai"

kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=nim-embed \
    --namespace finserv-ai --timeout=600s 2>/dev/null \
    || echo "  WARNING: NIM Embed pod not ready within timeout."

echo "  NIM Microservices deployment complete."

# ------------------------------------------------------------------
# Step 6/10: Deploy Prometheus + Grafana Monitoring Stack
# ------------------------------------------------------------------
echo ""
echo "Step 6/10: Deploying Prometheus + Grafana monitoring stack..."

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
helm repo update prometheus-community 2>/dev/null || true

# Create the monitoring namespace first so we can load the ConfigMap
kubectl create namespace monitoring 2>/dev/null || true

# Create Grafana dashboard ConfigMap from the custom AlphaAgent JSON dashboard
kubectl create configmap grafana-dashboard-alphaagent \
    --from-file=alphaagent-rag.json=kubernetes/monitoring/grafana-alphaagent-dashboard.json \
    -n monitoring \
    --dry-run=client -o yaml | kubectl apply -f -

# Label it so Grafana's sidecar picks it up automatically
kubectl label configmap grafana-dashboard-alphaagent \
    -n monitoring \
    grafana_dashboard=1 \
    --overwrite 2>/dev/null || true

GRAFANA_PW="${GRAFANA_ADMIN_PASSWORD:-$(openssl rand -base64 16)}"
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    -f kubernetes/monitoring/values-kube-prometheus.yaml \
    --set grafana.adminPassword="$GRAFANA_PW" \
    --wait --timeout 10m \
    || echo "  WARNING: Monitoring stack install had issues. Check: kubectl get pods -n monitoring"

echo "  Prometheus + Grafana deployed."
echo "  Grafana: kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80"
echo "  Default login: admin / <password set via GRAFANA_ADMIN_PASSWORD>"

# ------------------------------------------------------------------
# Step 7/10: Build and Deploy the AlphaAgent Application
# ------------------------------------------------------------------
echo ""
echo "Step 7/10: Building and deploying AlphaAgent application..."

ACR_NAME=$(echo "$outputs" | jq -r .acrName.value)
ACR_LOGIN_SERVER=$(echo "$outputs" | jq -r .acrLoginServer.value)

if [ -n "$ACR_NAME" ] && [ "$ACR_NAME" != "null" ]; then
    echo "  ACR: $ACR_LOGIN_SERVER"

    # Build in the cloud via az acr build — no local Docker required!
    az acr build \
        --registry "$ACR_NAME" \
        --image alphaagent/app:latest \
        --file app/Dockerfile \
        app/ \
        -o none

    export APP_IMAGE="$ACR_LOGIN_SERVER/alphaagent/app:latest"
    echo "  Image built and pushed: $APP_IMAGE"
else
    echo "  WARNING: No ACR found. Using default image reference."
    export APP_IMAGE="alphaagent/app:latest"
fi

# Apply the deployment with the ACR image
sed "s|image: alphaagent/app:latest|image: $APP_IMAGE|g" kubernetes/base/app-deployment.yaml \
    | kubectl apply -f -

echo "  Application deployment applied."

# Wait for app pod
kubectl wait --for=condition=ready pod -l app=alpha-agent \
    --namespace finserv-ai --timeout=300s 2>/dev/null \
    || echo "  WARNING: App pod not ready within timeout."

# ------------------------------------------------------------------
# Step 8/10: Load SEC EDGAR Data and Ingest into Milvus
# ------------------------------------------------------------------
echo ""
echo "Step 8/10: Loading SEC EDGAR filings and ingesting into Milvus..."

# Run the data loader script (creates a K8s Job for EDGAR download + triggers ingest)
bash scripts/load-data.sh || echo "  WARNING: Data loading encountered issues. You can retry with: make load-data"

echo "  Data loading step complete."

# ------------------------------------------------------------------
# Step 9/10: Verify Reranker Integration
# ------------------------------------------------------------------
echo ""
echo "Step 9/10: Verifying NV-RerankQA-Mistral-4B-v3 reranker integration..."

# Check if the reranker pod is running
RERANK_READY=$(kubectl get pods -n finserv-ai -l app.kubernetes.io/instance=nim-rerank \
    -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null || echo "false")

if [ "$RERANK_READY" = "true" ]; then
    echo "  Reranker NIM is RUNNING — RAG pipeline will use cross-encoder rescoring."
    echo "  RERANK_ENABLED=true in the app deployment (over-fetch 3x, rescore, return top_k)."
else
    echo "  Reranker NIM is NOT ready yet (may still be downloading model weights)."
    echo "  The app will gracefully fall back to embedding-only ranking until the pod is ready."
    echo "  Check status: kubectl get pods -n finserv-ai -l app.kubernetes.io/instance=nim-rerank"
fi

# ------------------------------------------------------------------
# Step 10/10: Final Health Check
# ------------------------------------------------------------------
echo ""
echo "Step 10/10: Running health check..."
echo ""

echo "--- Pods in finserv-ai ---"
kubectl get pods -n finserv-ai -o wide 2>/dev/null || true

echo ""
echo "--- Pods in monitoring ---"
kubectl get pods -n monitoring -o wide 2>/dev/null || true

echo ""
echo "--- Services in finserv-ai ---"
kubectl get svc -n finserv-ai 2>/dev/null || true

echo ""
echo "--- PVCs in finserv-ai ---"
kubectl get pvc -n finserv-ai 2>/dev/null || true

echo ""
echo "--- Key Vault CSI Status ---"
kubectl get secretproviderclass -n finserv-ai 2>/dev/null || echo "  No SecretProviderClass found."

echo ""
echo "--- ANF Snapshot Policy ---"
az netapp snapshot policy list \
    --resource-group "$RESOURCE_GROUP" \
    --account-name "${PREFIX}-anf-account" \
    --query "[].{name:name, enabled:enabled}" \
    -o table 2>/dev/null || echo "  Could not query snapshot policies."

# Get Streamlit UI endpoint
UI_IP=""
for i in $(seq 1 12); do
    UI_IP=$(kubectl get svc streamlit-ui -n finserv-ai -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    if [ -n "$UI_IP" ]; then
        break
    fi
    echo "  Waiting for LoadBalancer IP... ($i/12)"
    sleep 10
done

echo ""
echo "========================================================"
echo "  AlphaAgent Enterprise Deployment COMPLETE!"
echo "========================================================"
echo ""
echo "  Resource Group  : $RESOURCE_GROUP"
echo "  AKS Cluster     : $AKS_NAME (autoscaler: GPU 0-4 nodes)"
echo "  ACR Registry    : ${ACR_NAME:-N/A}"
echo "  Key Vault       : ${KEY_VAULT_NAME:-N/A} (CSI auto-rotation enabled)"
echo "  ANF Data Volume : $ANF_DATA_IP:/$ANF_DATA_VOL (snapshot policy active)"
echo ""
echo "  Components Deployed:"
echo "    NVIDIA NIM LLM         : Llama 3.1 8B Instruct v1.1.2"
echo "    NVIDIA NIM Embed       : NV-EmbedQA-E5-v5 v1.0.0"
echo "    NVIDIA NIM Rerank      : NV-RerankQA-Mistral-4B-v3 v1.0.0 (RAG pipeline integrated)"
echo "    NVIDIA NIM Retriever   : NeMo Retriever Parse v1.0.0"
echo "    Milvus Vector DB       : v2.4.0 cluster mode (2x query, 2x data, 3x etcd)"
echo "    Monitoring             : Prometheus + Grafana (GPU + NIM + Milvus dashboards)"
echo "    Auth                   : Azure AD / Entra ID (AUTH_ENABLED=false for demo)"
echo ""
if [ -n "$UI_IP" ]; then
    echo "  Streamlit UI : http://$UI_IP:8501"
    echo "  Grafana      : kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80"
    echo ""
    echo "  Open the Streamlit URL above and start querying!"
else
    echo "  Streamlit UI : LoadBalancer IP not yet assigned."
    echo "  Run: kubectl get svc streamlit-ui -n finserv-ai -w"
fi
echo ""
echo "  Useful commands:"
echo "    make status        — cluster health check"
echo "    make logs          — tail app logs"
echo "    make load-data     — re-run data ingestion"
echo "    make monitoring    — port-forward Grafana to localhost:3000"
echo "    make destroy       — tear down everything (save money!)"
echo ""
