# Project AlphaAgent: Financial Research Copilot

A production-grade, 4-layer Agentic AI architecture for Capital Markets.

This repository demonstrates the **Better Together** story of Microsoft Azure, NVIDIA AI, and Azure NetApp Files by deploying a fully sovereign, multi-agent document intelligence platform.

> [!WARNING]
> This is the pure enterprise deployment pattern targeting **Azure Kubernetes Service (AKS)** with dedicated GPU nodes. If you are looking for the simplified single-VM fallback, see the `backup/single-vm/` directory.

---

## 🏗️ 4-Layer Enterprise Architecture

This repository uses Infrastructure as Code (Bicep + Helm) to deploy:

1. **Data Layer**: Azure NetApp Files (Premium) hosting real SEC EDGAR filings (10-K, 10-Q). Data is accessed simultaneously via NFSv4.1 (for legacy apps) and the Object REST API natively in Python via `boto3` for zero-ETL AI processing.
2. **AI Processing Layer**: AKS cluster with NVIDIA GPU Operator. Hosts local **NVIDIA NIM microservices** via Helm:
   - NeMo Retriever (Multimodal PDF extraction)
   - NV-EmbedQA (Vectors)
   - NV-RerankQA (Retrieval scoring)
   - Nemotron Super 49B / Nano (LLM reasoning)
3. **Intelligence Layer**: **NVIDIA NeMo Agent Toolkit** orchestrating a 6-agent collaborative framework. Semantic search is powered by **Milvus** vector database, physically persisted on ANF NFS volumes and logically accelerated by NVIDIA **cuVS** (`GPU_CAGRA` index).
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

---

## 🌎 Full "Better Together" Context

The AlphaAgent repository is designed to showcase the pinnacle of enterprise sovereign AI by integrating three world-class pillars:

### 1. Azure NetApp Files (Zero Data Movement)

Historically, Financial Services Institutions (FSIs) have suffered from the "ETL paradigm"—duplicating massive troves of on-premises NAS PDFs into cloud object stores just to make them accessible to AI. AlphaAgent eliminates this using the **ANF File/Object Duality** feature.
Legacy batch jobs download SEC filings (10-K, 10-Q) and write them locally to ANF using the standard `NFSv4.1` POSIX protocol. Simultaneously, the AlphaAgent AI Python pipeline (`ingest.py`) reads those exact same files using `boto3` via the **S3-Compatible Object REST API**. This proves **Zero Data Movement (Zero-ETL)**, massively cutting storage costs and compliance risks.

### 2. NVIDIA AI (Hardware Acceleration & Sovereignty)

The stack abandons public API endpoints in favor of 100% data sovereignty via **NVIDIA NIM Microservices** deployed locally on Azure Kubernetes Service (AKS) GPU node pools (`Standard_NC24ads_A100_v4`).

- **NeMo Retriever** handles complex multimodal extraction of financial charts and tables from the raw PDFs.
- **Milvus Vector Database** is physically persisted on the ANF NFS premium tiers, but logically supercharged by the **NVIDIA `cuVS` (RAPIDS) algorithm** (`GPU_CAGRA` index) to provide sub-millisecond similarity search across billion-scale vector datasets.
- **Nemotron Super 49B / Llama 3.1** acts as the local LLM reasoning engine.

### 3. NeMo Agent Toolkit (Agentic Workflows)

Replacing rigid, linear RAG scripts, the application leverages the `nvidia-nat` open-source framework. A declarative YAML state machine orchestrates 6 distinct agents: an Orchestrator, SEC Fundamental Analyst, Earnings Sentiment Evaluator, Market News Specialist, Regulatory Compliance Officer, and Executive Summarizer. This provides highly parallelized, hallucination-resistant financial research generation.

---

## 🧠 Building AlphaAgent: The Engineering Journey

During the development of this repository, several critical design decisions were made to elevate this from a "toy" RAG application to a production-grade enterprise system:

1. **Rejecting the Single-VM Shortcut:** Initially, the architecture was conceived as a single-VM Docker Compose deployment. We explicitly rejected this. Enterprise AI demands high availability, rolling updates, and scalable node pools. We rebuilt the infrastructure using **Bicep** to target **Azure Kubernetes Service (AKS)**, utilizing Helm for the NVIDIA GPU Operator, Milvus, and the various NIM microservices. The single-VM code is preserved in `backup/single-vm/` for reference, but the core path is purely Kubernetes.
2. **Battling Hallucinations with NeMo Agent Toolkit (`nvidia-nat`):** Simple Python loop agents are prone to catastrophic hallucination when cross-referencing vast amounts of financial data. By integrating the NVIDIA NeMo Agent Toolkit and a declarative `workflow.yaml`, we implemented a strict state machine. We created dedicated tools (`market_data.py`, `compliance.py`) to ground the agents. Specifically, the **Compliance Agent** acts as an LLM-driven adversarial check to ensure the Orchestrator's final output adheres to strict FINRA/SEC regulatory guidelines before presenting it to the user.
3. **The S3 `boto3` Integration:** To truly prove the Azure NetApp Files "Zero-ETL" value proposition, we didn't just talk about it—we built it. We modified the `ingest.py` pipeline to specifically query the ANF Object REST API using standard `boto3` calls, validating that AI workloads can treat on-prem NAS folders as cloud-native S3 buckets instantly, with a seamless fallback to POSIX NFS mounts.
4. **NVIDIA cuVS Acceleration:** We identified that standard CPU-based HNSW vector indexes become a bottleneck as vector counts scale into the hundreds of millions. We updated the Milvus Helm charts and the ingestion script to leverage the NVIDIA RAPIDS `cuVS` algorithm (`GPU_CAGRA` index mode), completely shifting similarity search compute to the GPU tier for sub-millisecond lookups.
5. **Observability is Mandatory:** We integrated execution tracing into the Streamlit UI, allowing analysts to watch the agent chain-of-thought routing in real time, exposing which internal tools (Milvus, web search, compliance checks) were executed and how long they took.
