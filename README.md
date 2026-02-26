# Project AlphaAgent: Financial Research Copilot

A production-grade, 4-layer Agentic AI architecture for Capital Markets.

This repository demonstrates the **Better Together** story of Microsoft Azure, NVIDIA AI, and Azure NetApp Files by deploying a fully sovereign, multi-agent document intelligence platform.

> [!WARNING]
> This is the pure enterprise deployment pattern targeting **Azure Kubernetes Service (AKS)** with dedicated GPU nodes. If you are looking for the simplified single-VM fallback, see the `backup/single-vm/` directory.

---

## 🏗️ 4-Layer Enterprise Architecture

This repository uses Infrastructure as Code (Bicep + Helm) to deploy:

1. **Data Layer**: Azure NetApp Files (Premium) hosting real SEC EDGAR filings (10-K, 10-Q). Data is accessed simultaneously via NFSv4.1 (for K8s PVs) and the Object REST API (S3-compatible) for zero-ETL agent reads.
2. **AI Processing Layer**: AKS cluster with NVIDIA GPU Operator. Hosts local **NVIDIA NIM microservices** via Helm:
   - NeMo Retriever (Multimodal PDF extraction)
   - NV-EmbedQA (Vectors)
   - NV-RerankQA (Retrieval scoring)
   - Nemotron Super 49B / Nano (LLM reasoning)
3. **Intelligence Layer**: **NVIDIA NeMo Agent Toolkit** orchestrating a 6-agent collaborative framework. Semantic search is powered by **Milvus** vector database, persisted on ANF NFS volumes and accelerated by cuVS.
4. **Interface Layer**: Interactive Streamlit UI exposing agent thought processes, Milvus citations, and NeMo observability telemetry.

*All data and inference remain 100% within the Azure VNet. No external API calls are made for document analysis.*

---

## 🚀 Single-Command Deployment

The entire stack—Azure infrastructure, AKS cluster, GPU operator, Helm charts, data ingestion, and agent UI—is deployed automatically.

### Prerequisites

1. **Quota**: Your Azure subscription must have quota for AKS nodes (e.g., `Standard_D4s_v3` for system, `Standard_NC24ads_A100_v4` or equivalent for GPU).
2. **Tools**: `az`, `kubectl`, `helm`, `jq`, `make`.
3. **NGC Key**: An NVIDIA NGC API key to pull enterprise NIM containers.
4. **ANF Provider**: Ensure `Microsoft.NetApp` is registered in your Azure subscription.

### Deploy

```bash
# 1. Copy the template and fill in your details
cp .env.template .env

# 2. Deploy the architecture
make deploy NGC_API_KEY=your_key_here
```

---

## 📂 Repository Structure

| Path | Purpose |
|------|---------|
| `/infra` | Bicep templates for VNet, ANF, AKS, and Key Vault. |
| `/kubernetes` | Helm values and K8s manifests for the cluster workloads. |
| `/scripts` | Automated deployment and orchestration bash scripts. |
| `/app/workflow.yaml` | NeMo Agent Toolkit declarative agent definitions. |
| `/app/demo` | Python agent skill tools, data ingestion, and Streamlit UI. |
| `/docs` | Deep-dive architectures, failure modes, and talk tracks. |

---

## 🧹 Teardown

To avoid incurring ongoing Azure costs, strictly destroy the resource group after your session:

```bash
make destroy
```

---

## 📜 License

MIT License. See `LICENSE` for details.

## Hands-On Lab Guide
For a detailed, step-by-step workshop guide on deploying and testing this architecture, please refer to [docs/LAB_GUIDE.md](docs/LAB_GUIDE.md).
