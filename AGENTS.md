# Agent Instructions (for Codex / Contributors)

## Executive Architecture

- Target: **Azure Kubernetes Service (AKS)** with System + NVIDIA GPU Node Pools.
- Storage: **Azure NetApp Files NFSv4.1** mounted to `/mnt/anf` via PVCs.
- AI Layer: **NVIDIA NIM microservices** (Llama 3.1, NV-EmbedQA, NV-RerankQA, NeMo Retriever) running via Helm on AKS.
- Intelligence: **NVIDIA NeMo Agent Toolkit (`nvidia-nat`)** powering a 6-agent state machine.
- Vector DB: **Milvus** backed by ANF.
- Data: **Real SEC EDGAR filings** (AAPL, MSFT, TSLA) and earnings endpoints.
- Demo Flow: Deploy via `make deploy NGC_API_KEY=...` followed by `make load-data` to populate Milvus.

## What "Working" Means

- Multi-agent deployment comes up flawlessly behind an AKS load balancer.
- Streamlit UI (`app/ui.py`) natively invokes the NeMo `Runner` class using `workflow.yaml`.
- UI can:
  - Generate grounded investment memos using NeMo Retriever parsed data.
  - Coordinate the SEC, Earnings, and News agents via the Orchestrator.
  - Show the agent's chain-of-thought routing (trace).
  - Run a compliance check via the LLM against internal policies.
- Data lives purely on resilient ANF mounts.

## Multi-Agent Architecture (NeMo Worker Topology)

The app uses 6 distinct specialized agent personas orchestrated via `nvidia-nat`:

1. **Orchestrator** — Routes queries, decomposes tasks to sub-agents.
2. **SEC Filing Agent** — Performs Milvus semantic searches on ANF 10-K data.
3. **Earnings Agent** — Calls real market data transcripts to gauge sentiment.
4. **News Agent** — Fetches macro/market news affecting the ticker.
5. **Compliance Agent** — LLM-driven check against SEC/FINRA templates.
6. **Summarization Agent** — Synthesizes final investment briefs.

## Better Together Messaging

When writing UI text, logs, or documentation, reinforce these pillars:

1. **Data Stays In Place (File & Object Duality)** — ANF NFSv4.1 for legacy writes and native `boto3` S3-compatible Object REST API for AI reads, proving zero ETL.
2. **GPU-Accelerated Intelligence** — NVIDIA NIMs, sub-200ms inference on Azure infrastructure.
3. **Agentic AI for the Enterprise** — NeMo Agent Toolkit orchestration, avoiding linear scripts.
4. **Production-Ready, Not a Prototype** — Stateful Kubernetes (AKS), hardware-accelerated Milvus (`cuVS` RAPIDS algorithm), Rerankers, and NeMo Retrievers.

## Known Limits & Future Backlog

- Expand internal logic of `market_data.py` to hit real Bloomberg/Refinitiv downstream APIs.
