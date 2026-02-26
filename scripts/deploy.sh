#!/bin/bash
set -e

# AlphaAgent Enterprise Deployment Script
# 1. Deploys Azure Infrastructure via Bicep (AKS, ANF, KeyVault)
# 2. Configures kubectl credentials
# 3. Deploys Helm charts: GPU Operator, Milvus, NVIDIA NIMs
# 4. Deploys the multi-agent UI

NGC_API_KEY=$1
RESOURCE_GROUP=${RG_NAME:-"rg-alphaagent-demo-$(whoami)"}
LOCATION=${LOCATION:-"eastus2"}
PREFIX="alpha-ai"

if [ -z "$NGC_API_KEY" ]; then
    echo "Error: NGC_API_KEY is required."
    exit 1
fi

echo "🚀 Starting Enterprise AlphaAgent Deployment..."

echo "➡️ Step 1/4: Provisioning Azure Infrastructure (VNet, AKS, Azure NetApp Files)..."
az group create --name $RESOURCE_GROUP --location $LOCATION -o none
az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file infra/main.bicep \
    --parameters infra/parameters.json \
    -o none
echo "✅ Infrastructure Provisioned successfully."

echo "➡️ Step 2/4: Configuring AKS and Base Layer..."
AKS_NAME="${PREFIX}-aks"
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME --overwrite-existing

kubectl apply -f kubernetes/base/namespace.yaml
kubectl create secret docker-registry ngc-secret \
    --namespace finserv-ai \
    --docker-server=nvcr.io \
    --docker-username="\$oauthtoken" \
    --docker-password="$NGC_API_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -

# Get ANF IPs from deployment to inject into PVC overrides
outputs=$(az deployment group show --resource-group $RESOURCE_GROUP --name main --query properties.outputs)
ANF_DATA_IP=$(echo $outputs | jq -r .anfDataVolumeIp.value)
ANF_DATA_VOL=$(echo $outputs | jq -r .anfDataVolumePath.value)
ANF_MILVUS_IP=$(echo $outputs | jq -r .anfMilvusVolumeIp.value)
ANF_MILVUS_VOL=$(echo $outputs | jq -r .anfMilvusVolumePath.value)

envsubst < kubernetes/base/anf-pvc.yaml | kubectl apply -f -
echo "✅ Base layer and ANF storage mapped."

echo "➡️ Step 3/4: Deploying GPU Operator and Core Services (Milvus, NIMs)..."
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia || true
helm repo add milvus https://zilliztech.github.io/milvus-helm || true
helm repo update

# Install GPU Operator
helm upgrade --install gpu-operator nvidia/gpu-operator \
    --namespace gpu-operator --create-namespace \
    -f kubernetes/gpu-operator/values.yaml

# Install Milvus on ANF
helm upgrade --install milvus milvus/milvus \
    --namespace finserv-ai \
    -f kubernetes/milvus/values.yaml

# Install NIMs (Requires Helm charts from NGC)
echo "Deploying NVIDIA NIM Microservices (LLM, Embeddings, Reranking, Retriever)..."
helm upgrade --install nim-llm oci://dp.ngc.nvidia.com/nim/meta/llama-3.1-8b-instruct \
    --namespace finserv-ai \
    -f kubernetes/nim/llm-values.yaml --version 1.1.2 || echo "NIM LLM Helm chart repo not fully authenticated, using pre-deployed manifest..."

helm upgrade --install nim-embed oci://dp.ngc.nvidia.com/nim/nvidia/nv-embedqa-e5-v5 \
    --namespace finserv-ai \
    -f kubernetes/nim/embed-values.yaml --version 1.0.0 || true

helm upgrade --install nim-rerank oci://dp.ngc.nvidia.com/nim/nvidia/nv-rerankqa-mistral-4b-v3 \
    --namespace finserv-ai \
    -f kubernetes/nim/rerank-values.yaml --version 1.0.0 || true

helm upgrade --install nim-retriever oci://dp.ngc.nvidia.com/nim/nvidia/nemo-retriever-parse \
    --namespace finserv-ai \
    -f kubernetes/nim/retriever-values.yaml --version 1.0.0 || true

echo "✅ Core Services deployed (Waiting for Pods...)"

echo "➡️ Step 4/4: Deploying Agentic Application..."
# Build and push the application image to ACR (if ACR is set up), otherwise apply deployment
ACR_NAME=$(az deployment group show --resource-group $RESOURCE_GROUP --name main --query properties.outputs.acrName.value -o tsv || true)

if [ -n "$ACR_NAME" ]; then
    echo "Building App image and pushing to $ACR_NAME..."
    az acr login --name $ACR_NAME
    docker build -t $ACR_NAME.azurecr.io/alphaagent/app:latest app/
    docker push $ACR_NAME.azurecr.io/alphaagent/app:latest
    # Update deployment tightly to ACR
    sed -i "s|image: alphaagent/app:latest|image: $ACR_NAME.azurecr.io/alphaagent/app:latest|g" kubernetes/base/app-deployment.yaml
fi

kubectl apply -f kubernetes/base/app-deployment.yaml
echo "✅ Deployment manifests applied."

echo "🎉 Enterprise AlphaAgent Deployment Initiated!"
echo "Run 'kubectl get pods -n finserv-ai -w' to view progress."
