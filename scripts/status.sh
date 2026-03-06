#!/bin/bash
# AlphaAgent Status Check — Displays cluster health, pod status, and endpoints.

RESOURCE_GROUP=${RG_NAME:-"DNvidiaANF"}
PREFIX=${PREFIX:-"alpha-ai"}
AKS_NAME="${PREFIX}-aks"
NAMESPACE="finserv-ai"

echo "========================================================"
echo "  AlphaAgent Cluster Status"
echo "  Resource Group: $RESOURCE_GROUP"
echo "========================================================"

echo ""
echo "--- AKS Node Status ---"
kubectl get nodes -o wide 2>/dev/null || echo "  Cannot reach AKS. Run: az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME"

echo ""
echo "--- GPU Resources ---"
kubectl describe nodes | grep -A5 "nvidia.com/gpu" 2>/dev/null || echo "  No GPU resources detected."

echo ""
echo "--- AKS Autoscaler Status ---"
kubectl get nodes -l agentpool=gpupool -o custom-columns="NAME:.metadata.name,STATUS:.status.conditions[-1].type,READY:.status.conditions[-1].status" 2>/dev/null || true
echo "  (GPU pool autoscales between 0-4 nodes based on NIM pod demand)"

echo ""
echo "--- Pods in $NAMESPACE ---"
kubectl get pods -n "$NAMESPACE" -o wide 2>/dev/null

echo ""
echo "--- Pods in monitoring ---"
kubectl get pods -n monitoring -o wide 2>/dev/null || echo "  Monitoring namespace not found."

echo ""
echo "--- Pods in gpu-operator ---"
kubectl get pods -n gpu-operator -o wide 2>/dev/null || echo "  GPU Operator namespace not found."

echo ""
echo "--- Services in $NAMESPACE ---"
kubectl get svc -n "$NAMESPACE" 2>/dev/null

echo ""
echo "--- PVCs in $NAMESPACE ---"
kubectl get pvc -n "$NAMESPACE" 2>/dev/null

echo ""
echo "--- NIM Health Checks ---"
for nim_svc in nim-llm nim-embed nim-rerank nim-retriever; do
    NIM_IP=$(kubectl get svc "$nim_svc" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null)
    if [ -n "$NIM_IP" ]; then
        HEALTH=$(kubectl exec -n "$NAMESPACE" deploy/alpha-agent-app -- \
            curl -s -o /dev/null -w "%{http_code}" "http://$NIM_IP:8000/v1/health/ready" 2>/dev/null || echo "N/A")
        echo "  $nim_svc: $HEALTH"
    else
        echo "  $nim_svc: Service not found"
    fi
done

echo ""
echo "--- Reranker RAG Integration ---"
RERANK_ENABLED=$(kubectl get deploy alpha-agent-app -n "$NAMESPACE" \
    -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="RERANK_ENABLED")].value}' 2>/dev/null || echo "unknown")
echo "  RERANK_ENABLED=$RERANK_ENABLED"
RERANK_READY=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/instance=nim-rerank \
    -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null || echo "false")
echo "  Reranker pod ready: $RERANK_READY"

echo ""
echo "--- Key Vault CSI ---"
kubectl get secretproviderclass -n "$NAMESPACE" 2>/dev/null || echo "  No SecretProviderClass configured."

echo ""
echo "--- ANF Snapshot Policy ---"
az netapp snapshot policy list \
    --resource-group "$RESOURCE_GROUP" \
    --account-name "${PREFIX}-anf-account" \
    --query "[].{name:name, enabled:enabled, hourly:hourlySchedule.snapshotsToKeep, daily:dailySchedule.snapshotsToKeep}" \
    -o table 2>/dev/null || echo "  Could not query snapshot policies."

echo ""
echo "--- Helm Releases ---"
echo "  finserv-ai:"
helm list -n "$NAMESPACE" 2>/dev/null
echo "  gpu-operator:"
helm list -n gpu-operator 2>/dev/null
echo "  monitoring:"
helm list -n monitoring 2>/dev/null

echo ""
echo "--- Streamlit UI Endpoint ---"
UI_IP=$(kubectl get svc streamlit-ui -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
if [ -n "$UI_IP" ]; then
    echo "  Streamlit: http://$UI_IP:8501"
else
    echo "  LoadBalancer IP not yet assigned. Run: kubectl get svc streamlit-ui -n $NAMESPACE -w"
fi

echo ""
echo "--- Grafana Dashboard ---"
echo "  Run: kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80"
echo "  Login: admin / <password set via GRAFANA_ADMIN_PASSWORD>"
