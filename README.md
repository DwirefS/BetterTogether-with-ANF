# Project AlphaAgent: Financial Research Copilot

A production-grade, 4-layer Agentic AI architecture for Capital Markets — built on Azure, NVIDIA AI, and Azure NetApp Files.

This repository deploys a fully sovereign, multi-agent document intelligence platform that analyzes SEC EDGAR filings using NVIDIA NIM microservices, Milvus vector search, and NeMo Agent Toolkit orchestration. All data and inference stay 100% within the Azure VNet.

> **Conference Demo**: This stack is designed for the "Better Together with ANF" presentation showcasing the convergence of Azure NetApp Files, NVIDIA AI, and Azure Kubernetes Service.

---

## Architecture

```
                           ┌──────────────────────────────────────┐
                           │       Streamlit UI (Port 8501)       │
                           │    Azure AD Auth  |  Agent Traces    │
                           └──────────────┬───────────────────────┘
                                          │
                ┌─────────────────────────┼─────────────────────────┐
                │          NeMo Agent Toolkit (nvidia-nat)          │
                │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
                │  │ SEC Agent│ │Earnings  │ │  News Agent      │  │
                │  │ (RAG)   │ │ Agent    │ │  (Market Data)   │  │
                │  └────┬─────┘ └──────────┘ └──────────────────┘  │
                │       │  ┌───────────┐  ┌─────────────────────┐  │
                │       │  │Compliance │  │ Summarization Agent │  │
                │       │  │  Agent    │  │ (Executive Brief)   │  │
                │       │  └───────────┘  └─────────────────────┘  │
                └───────┼──────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────────────────────────┐
        │               ▼                                   │
        │  ┌─────────────────────┐  ┌────────────────────┐  │
        │  │  NV-EmbedQA NIM    │  │  Llama 3.1 8B NIM  │  │
        │  │  (Vectorization)   │  │  (LLM Reasoning)   │  │
        │  └─────────┬──────────┘  └────────────────────┘  │
        │            │                                      │
        │  ┌─────────▼──────────┐  ┌────────────────────┐  │
        │  │ NV-RerankQA NIM   │  │ NeMo Retriever NIM │  │
        │  │ (Cross-Encoder)   │  │ (PDF Extraction)   │  │
        │  └─────────┬──────────┘  └────────────────────┘  │
        │            │              AKS GPU Pool (V100)     │
        └────────────┼─────────────────────────────────────┘
                     │
        ┌────────────▼─────────────────────────────────────┐
        │  Milvus Vector DB (Cluster Mode)                  │
        │  2x QueryNode | 2x DataNode | 3x etcd            │
        │  IVF_FLAT COSINE Index on ANF NFS                 │
        └────────────┬─────────────────────────────────────┘
                     │
        ┌────────────▼─────────────────────────────────────┐
        │  Azure NetApp Files (Premium NFS)                 │
        │  ┌──────────────┐  ┌───────────────────────────┐ │
        │  │ SEC Filings  │  │ Milvus Vectors + WAL      │ │
        │  │ (NFS + S3)   │  │ (Persistent Volume)       │ │
        │  └──────────────┘  └───────────────────────────┘ │
        │  Snapshot Policy: 6 hourly / 7 daily / 4 weekly  │
        └──────────────────────────────────────────────────┘
```

---

## Features

**AI Processing** — 4 NVIDIA NIM microservices (Llama 3.1 8B, NV-EmbedQA-E5-v5, NV-RerankQA-Mistral-4B-v3, NeMo Retriever Parse) deployed as Helm charts on AKS GPU nodes.

**RAG Pipeline with Reranker** — The retrieval pipeline embeds queries via NV-EmbedQA, over-fetches 3x candidates from Milvus, then rescores with the NV-RerankQA cross-encoder for 15-25% precision improvement. Toggleable via `RERANK_ENABLED` env var.

**6-Agent Orchestration** — NeMo Agent Toolkit (`nvidia-nat`) state machine coordinates an Orchestrator, SEC Analyst, Earnings Evaluator, News Specialist, Compliance Officer, and Executive Summarizer.

**Zero-ETL Storage** — Azure NetApp Files provides simultaneous NFS and S3 Object REST API access. Legacy systems write files via NFS; the AI pipeline reads them via `boto3` — no data movement.

**Cluster-Mode Milvus** — High-availability vector DB with 2x query replicas, 2x data replicas, and 3-node etcd Raft consensus. Persisted on ANF NFS.

**AKS Autoscaler** — GPU node pool scales between 0-4 nodes based on NIM pod demand, achieving 50-70% cost reduction during idle periods.

**Azure AD Authentication** — MSAL-based OIDC login gate for the Streamlit UI (`AUTH_ENABLED=true`). Supports sign-in, session management, and sign-out.

**Key Vault CSI Driver** — Secrets (NGC API key, Azure AD credentials, ANF S3 keys) auto-rotate from Azure Key Vault every 2 minutes via the Secrets Store CSI driver.

**Prometheus + Grafana Monitoring** — Full observability stack with GPU metrics (DCGM Exporter), NIM inference latency/throughput, Milvus query performance, and custom AlphaAgent dashboard. Includes alerting rules for GPU underutilization, high memory, and latency spikes.

**ANF Snapshot Policy** — Automated disaster recovery with 6 hourly, 7 daily, 4 weekly, and 12 monthly snapshots for both data and Milvus volumes.

---

## Quick Start

### Prerequisites

1. **Azure Subscription** with GPU VM quota (e.g., `Standard_NC6s_v3` or `Standard_NC24ads_A100_v4`)
2. **CLI Tools**: `az`, `kubectl`, `helm`, `jq`, `make` (install via `az aks install-cli` for kubectl)
3. **NVIDIA NGC API Key**: Get from [NGC Portal](https://org.ngc.nvidia.com/) — Profile — Setup — Generate API Key
4. **Azure Provider**: `Microsoft.NetApp` registered in your subscription

### Deploy

```bash
# 1. Clone and configure
git clone https://github.com/DwirefS/BetterTogether-with-ANF.git
cd BetterTogether-with-ANF
cp .env.template .env
# Edit .env and set NGC_API_KEY

# 2. Rebuild ARM template if main.bicep was modified
make bicep-build

# 3. Deploy everything (10-step automated pipeline)
make deploy NGC_API_KEY=nvapi-your-key-here
```

The deploy script provisions Azure infrastructure (VNet, AKS, ANF, Key Vault), installs the GPU Operator, deploys Milvus and 4 NIM microservices, sets up monitoring, builds the app image, loads SEC EDGAR filings, and prints the Streamlit URL.

### Post-Deploy

```bash
make status        # Cluster health, NIM status, reranker integration, snapshot policy
make logs          # Tail Streamlit app logs
make monitoring    # Port-forward Grafana to localhost:3000
make port-forward  # Port-forward Streamlit to localhost:8501
make destroy       # Tear down everything
```

---

## Repository Structure

```
.
├── app/
│   ├── ui.py                      # Streamlit UI with Azure AD auth gate
│   ├── ingest.py                  # Vector ingestion pipeline (NIM Embed -> Milvus)
│   ├── workflow.yaml              # NeMo Agent Toolkit 6-agent state machine
│   ├── Dockerfile                 # App container (built via az acr build)
│   ├── requirements.txt           # Python deps (streamlit, pymilvus, msal, etc.)
│   └── alpha_tools/
│       ├── nim_client.py          # NIM API client (LLM, Embed, Rerank, Retriever)
│       ├── anf_milvus_search.py   # RAG retrieval with reranker integration
│       ├── market_data.py         # Mock market data (with real API integration guide)
│       └── compliance.py          # LLM-powered FINRA/SEC compliance checker
├── infra/
│   ├── main.bicep                 # Azure IaC (VNet, AKS, ANF, KV, Snapshots, CSI)
│   ├── main.json                  # Compiled ARM template (from bicep build)
│   └── parameters.json            # Deployment parameters
├── kubernetes/
│   ├── base/
│   │   ├── namespace.yaml         # finserv-ai namespace
│   │   ├── anf-pvc.yaml           # ANF NFS PersistentVolumes (envsubst)
│   │   └── app-deployment.yaml    # App Deployment + Service + CSI mount
│   ├── nim/
│   │   ├── llm-values.yaml        # Llama 3.1 8B NIM Helm values
│   │   ├── embed-values.yaml      # NV-EmbedQA NIM Helm values
│   │   ├── rerank-values.yaml     # NV-RerankQA NIM Helm values
│   │   └── retriever-values.yaml  # NeMo Retriever Parse NIM Helm values
│   ├── milvus/
│   │   └── values.yaml            # Milvus cluster mode Helm values
│   ├── gpu-operator/
│   │   └── values.yaml            # GPU Operator + DCGM Exporter values
│   ├── secrets/
│   │   └── keyvault-csi.yaml      # Azure Key Vault CSI SecretProviderClass
│   └── monitoring/
│       ├── values-kube-prometheus.yaml     # Prometheus + Grafana Helm values
│       └── grafana-alphaagent-dashboard.json  # Custom Grafana dashboard
├── scripts/
│   ├── deploy.sh                  # 10-step end-to-end deployment pipeline
│   ├── status.sh                  # Cluster health check
│   ├── logs.sh                    # Log viewer
│   ├── load-data.sh               # SEC EDGAR download + Milvus ingestion
│   └── destroy.sh                 # Resource group teardown
├── Makefile                       # CLI shortcuts
├── .env.template                  # Environment variable template
└── README.md                      # This file
```

---

## Component Inventory

| Layer | Component | Version | Purpose |
|-------|-----------|---------|---------|
| Infra | Azure VNet | — | Network isolation (AKS + ANF subnets) |
| Infra | Azure NetApp Files | Premium NFS | Persistent storage for filings + vectors |
| Infra | Azure Key Vault | — | Secret management with CSI auto-rotation |
| Infra | AKS | 2023-10-01 API | Container orchestration with GPU autoscaler |
| AI | NIM LLM (Llama 3.1 8B) | v1.1.2 | Reasoning engine |
| AI | NIM Embed (NV-EmbedQA-E5-v5) | v1.0.0 | Text to 1024-dim vectors |
| AI | NIM Rerank (NV-RerankQA-Mistral-4B-v3) | v1.0.0 | Cross-encoder rescoring |
| AI | NIM Retriever Parse | v1.0.0 | Multimodal PDF extraction |
| DB | Milvus | v2.4.0 | Vector database (cluster mode, IVF_FLAT) |
| Agent | NeMo Agent Toolkit (nvidia-nat) | >=0.3.0 | 6-agent state machine orchestrator |
| Ops | GPU Operator + DCGM Exporter | latest | GPU driver management + metrics |
| Ops | kube-prometheus-stack | latest | Prometheus + Grafana + Alertmanager |
| App | Streamlit | 1.42.0 | Interactive UI |
| Auth | MSAL | >=1.28.0 | Azure AD OIDC authentication |

---

## Cost Optimization

The architecture includes several cost-saving features for demo/development use:

- **GPU Autoscaler**: Scales to 0 GPU nodes when idle (~$0 when not running inference)
- **CPU-only Milvus**: Uses IVF_FLAT index instead of GPU_CAGRA (saves 1 GPU node)
- **Standard ANF tier**: Uses Standard instead of Premium/Ultra (sufficient for demo data volumes)
- **Mock market data**: Avoids expensive Bloomberg/Refinitiv API subscriptions
- **V100 (NC6s_v3)**: ~$0.90/hr vs A100 at ~$3.67/hr (8B model fits in 16GB VRAM with NIM quantization)

---

## Teardown

```bash
make destroy
```

This deletes the entire resource group including all Azure resources. ANF volumes, AKS cluster, Key Vault, and all data will be permanently removed.

---

## License

MIT License. See `LICENSE` for details.
