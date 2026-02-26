#!/bin/bash
set -e

# AlphaAgent Data Loader
# Downloads real SEC EDGAR filings (10-K) for the demo, places them on the ANF NFS mount,
# and triggers the NeMo Retriever ingestion K8s Job.

echo "📥 Preparing to load real EDGAR SEC filings to Azure NetApp Files..."

# Depending on where this script is run (on a bastion, laptop, or inside a K8s utility pod),
# the target path for ANF needs to be accessible. Since the demo uses an architecture where
# the ANF is primarily accessed by the AKS pods, we will deploy a Kubernetes Job to download
# and ingest the data directly into the cluster's PVC.

cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: edgar-data-loader
  namespace: finserv-ai
spec:
  template:
    spec:
      containers:
      - name: loader
        image: python:3.11-slim
        command:
        - /bin/bash
        - -c
        - |
          echo "Installing SEC EDGAR Downloader..."
          pip install sec-edgar-downloader
          
          echo "Downloading 10-K filings for AAPL, MSFT, and TSLA..."
          python -c "
from sec_edgar_downloader import Downloader
dl = Downloader('NVIDIA_Demo', 'demo@nvidia.com', '/mnt/anf/data')
for ticker in ['AAPL', 'MSFT', 'TSLA']:
    print(f'Fetching latest 10-K for {ticker}...')
    dl.get('10-K', ticker, amount=1, download_details=True)
"
          echo "✅ Documents downloaded to ANF via PVC."
        volumeMounts:
        - name: anf-data
          mountPath: /mnt/anf/data
      restartPolicy: Never
      volumes:
      - name: anf-data
        persistentVolumeClaim:
          claimName: anf-data-pvc
  backoffLimit: 1
EOF

echo "✅ EDGAR Data Loader Job submitted to AKS."
echo "Waiting for SEC documents to download (this takes about 1-2 minutes)..."
kubectl wait --for=condition=complete job/edgar-data-loader -n finserv-ai --timeout=300s

echo "🚀 Triggering Milvus Vector Ingestion via the AlphaAgent App pod..."
POD_NAME=$(kubectl get pods -n finserv-ai -l app=alpha-agent -o jsonpath='{.items[0].metadata.name}')

if [ -n "$POD_NAME" ]; then
    echo "Executing NeMo Retriever ingestion on pod: $POD_NAME"
    kubectl exec -n finserv-ai $POD_NAME -- python /app/ingest.py
    echo "✅ Ingestion complete. Vectors are stored securely in Milvus on ANF."
else
    echo "❌ Error: Could not find the alpha-agent pod to run ingestion. Make sure 'make deploy' was fully successful."
fi
