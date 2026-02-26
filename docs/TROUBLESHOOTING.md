# AlphaAgent — Enterprise Troubleshooting Guide (AKS)

## Top Failure Modes & Solutions

### 1. GPU Quota Not Available

**Symptoms:** Bicep deployment fails with "quota exceeded" or "SkuNotAvailable" for the AKS GPU Node Pool.

**Fix:**

```bash
# Check available GPU VM sizes in your region
az vm list-skus --location eastus2 --resource-type virtualMachines \
  --query "[?contains(name,'NC') || contains(name,'ND')].{Name:name, Available:restrictions}" -o table

# Request quota increase via Azure Portal or CLI
az quota update --resource-name "standardNCADSA100v4Family" \
  --scope "/subscriptions/<sub>/providers/Microsoft.Compute/locations/eastus2" \
  --limit 24
```

### 2. ANF NFS PVC Sticks in "Pending"

**Symptoms:** Pods leveraging the `anf-data-pvc` are stuck in "Pending".

**Fix:**

```bash
# Describe the PVC to see binding errors
kubectl describe pvc anf-data-pvc -n finserv-ai

# Verify the ANF Volume IP matches the PV configuration
kubectl get pv anf-data-pv -o yaml | grep server

# Check if the AKS VNet is properly peered/delegated to the ANF Subnet
az network vnet subnet show -g <rg> --vnet-name <vnet> -n <anf-subnet>
```

### 3. NVIDIA NIM Pods Crashlooping (OOM)

**Symptoms:** `nim-llm` or `nim-embed` pods show `CrashLoopBackOff` or `OOMKilled`.

**Fix:**

```bash
# Check the pod logs to see if it ran out of GPU VRAM
kubectl logs -l app.kubernetes.io/name=llama-3.1-8b-instruct -n finserv-ai --tail 50

# Exec into a generic pod and run helm to check resources
helm status nim-llm -n finserv-ai

# If VRAM is the issue, either scale up the AKS GPU nodes or lower the `gpu` resource requests in `kubernetes/nim/llm-values.yaml`.
```

### 4. NGC Pull Secrets Fail

**Symptoms:** `ImagePullBackOff` for the NIM pods or `alphaagent-app`.

**Fix:**

```bash
# Check the failing pod's events
kubectl describe pod <pod-name> -n finserv-ai

# Re-create the docker registry secret if the API key was injected incorrectly
kubectl create secret docker-registry ngc-secret \
    --namespace finserv-ai \
    --docker-server=nvcr.io \
    --docker-username="\$oauthtoken" \
    --docker-password="<NEW_NGC_API_KEY>" \
    --dry-run=client -o yaml | kubectl apply -f -
```

### 5. `make load-data` Ingestion Error

**Symptoms:** The script says "Could not find the alpha-agent pod to run ingestion."

**Fix:**

```bash
# Verify the Streamlit app actually deployed
kubectl get pods -n finserv-ai -l app=alpha-agent

# Check if the Streamlit app is crashing due to a missing environment variable or failed Milvus connection
kubectl logs -l app=alpha-agent -n finserv-ai

# If pods are running, manually trigger ingestion:
kubectl exec -n finserv-ai <pod-name> -- python /app/ingest.py
```

## Quick Health Check Commands

```bash
# General Cluster Health
make status                          # Show all endpoints & node statuses
kubectl get nodes -o wide            # Ensure GPU nodes are 'Ready'
kubectl get pods -n finserv-ai -w    # Watch all enterprise pods spin up

# Service Diagnostics
kubectl logs -l app.kubernetes.io/name=milvus -n finserv-ai
kubectl logs -l app=alpha-agent -n finserv-ai
kubectl get svc -n finserv-ai        # Get external IPs for the UI and DBs
```
