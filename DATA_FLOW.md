# AlphaAgent — End-to-End Data Flow

> How a SEC filing becomes an investment memo.

---

## The Two Phases

AlphaAgent has two distinct phases: **Ingestion** (happens once, offline) and
**Query** (happens every time a user asks a question). Every component in the
NVIDIA + Azure stack plays a specific role in one or both phases.

---

## Phase 1: Ingestion (Offline — `ingest.py` + `load-data.sh`)

This is the "prep work" that happens before any user ever asks a question.
Raw SEC EDGAR filings (10-K annual reports for AAPL, MSFT, TSLA) get
downloaded, cleaned, fingerprinted, and stored.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INGESTION PIPELINE                          │
│                                                                    │
│  SEC EDGAR (public internet)                                       │
│       │                                                            │
│       ▼                                                            │
│  ┌──────────────┐    K8s Job: edgar-data-loader                    │
│  │  Download     │   (load-data.sh submits this)                   │
│  │  10-K PDFs    │   Uses: sec-edgar-downloader Python package     │
│  └──────┬───────┘                                                  │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────────────┐          │
│  │            Azure NetApp Files (ANF)                   │          │
│  │                                                       │          │
│  │  NFS Mount: /mnt/anf/data/                            │          │
│  │  ├── AAPL/10-K/0000320193-xx.pdf                      │          │
│  │  ├── MSFT/10-K/0000789019-xx.pdf                      │          │
│  │  └── TSLA/10-K/0001318605-xx.pdf                      │          │
│  │                                                       │          │
│  │  Also accessible via S3 Object REST API (boto3)       │          │
│  │  for zero-ETL data access without copying files.      │          │
│  └──────────────────────────────┬────────────────────────┘          │
│                                 │                                   │
│                                 ▼                                   │
│  ┌──────────────────────────────────────────────────────┐          │
│  │         STEP 1: PDF Extraction                        │          │
│  │                                                       │          │
│  │  PRIMARY: NeMo Retriever Parse NIM                    │          │
│  │  ┌─────────────────────────────────────────┐          │          │
│  │  │ nim_client.extract_pdf()                 │          │          │
│  │  │ POST http://nim-retriever:8000/v1/extract│          │          │
│  │  │                                          │          │          │
│  │  │ What it does:                            │          │          │
│  │  │  - Object detection (find tables/charts) │          │          │
│  │  │  - OCR (read text accurately)            │          │          │
│  │  │  - Layout analysis (understand structure)│          │          │
│  │  │  - Returns clean structured text + JSON  │          │          │
│  │  └─────────────────────────────────────────┘          │          │
│  │                                                       │          │
│  │  FALLBACK: PyPDFLoader (if NeMo Retriever is down)    │          │
│  │  ┌─────────────────────────────────────────┐          │          │
│  │  │ Basic line-by-line text extraction.       │          │          │
│  │  │ No table awareness. No layout analysis.  │          │          │
│  │  │ Sufficient for demo, poor for production.│          │          │
│  │  └─────────────────────────────────────────┘          │          │
│  │                                                       │          │
│  │  STATUS: ⚠️  NeMo Retriever code exists but the       │          │
│  │  exact API shape needs validation once NV-Ingest is   │          │
│  │  deployed. NV-Ingest is a multi-container pipeline,   │          │
│  │  not a single NIM — may need its own Helm deployment. │          │
│  └──────────────────────────────┬────────────────────────┘          │
│                                 │                                   │
│                                 ▼                                   │
│  ┌──────────────────────────────────────────────────────┐          │
│  │         STEP 2: Text Chunking                         │          │
│  │                                                       │          │
│  │  RecursiveCharacterTextSplitter (LangChain)           │          │
│  │  chunk_size=1000, overlap=100                         │          │
│  │                                                       │          │
│  │  Splits long filing text into ~1000-character chunks   │          │
│  │  with 100-char overlap so no sentence is cut in half. │          │
│  └──────────────────────────────┬────────────────────────┘          │
│                                 │                                   │
│                                 ▼                                   │
│  ┌──────────────────────────────────────────────────────┐          │
│  │         STEP 3: Embedding (Vectorization)             │          │
│  │                                                       │          │
│  │  NIM: NV-EmbedQA-E5-v5 (NeMo Retriever Embedding)    │          │
│  │  ┌─────────────────────────────────────────┐          │          │
│  │  │ nim_client.get_embeddings()              │          │          │
│  │  │ POST http://nim-embed:8000/v1/embeddings │          │          │
│  │  │                                          │          │          │
│  │  │ Input:  "Apple's revenue grew 2.9%..."   │          │          │
│  │  │ Output: [0.023, -0.891, 0.445, ...]      │          │          │
│  │  │         (1024-dimensional float vector)   │          │          │
│  │  │                                          │          │          │
│  │  │ Each chunk becomes a numerical            │          │          │
│  │  │ "fingerprint" capturing its meaning.      │          │          │
│  │  └─────────────────────────────────────────┘          │          │
│  │                                                       │          │
│  │  STATUS: ✅ Fully implemented with retry logic.       │          │
│  └──────────────────────────────┬────────────────────────┘          │
│                                 │                                   │
│                                 ▼                                   │
│  ┌──────────────────────────────────────────────────────┐          │
│  │         STEP 4: Vector Storage                        │          │
│  │                                                       │          │
│  │  Milvus Vector Database (cluster mode on AKS)         │          │
│  │  ┌─────────────────────────────────────────┐          │          │
│  │  │ Collection: "sec_filings"                │          │          │
│  │  │ Index: IVF_FLAT, COSINE similarity       │          │          │
│  │  │ Fields: id, vector(1024), text, source   │          │          │
│  │  │                                          │          │          │
│  │  │ Storage: ANF NFS PVC (anf-milvus-pvc)    │          │          │
│  │  │ Milvus data files live on NetApp storage │          │          │
│  │  │ = enterprise durability + snapshots.      │          │          │
│  │  └─────────────────────────────────────────┘          │          │
│  │                                                       │          │
│  │  STATUS: ✅ Fully implemented. Cluster mode with      │          │
│  │  2x queryNode, 2x dataNode, 3x etcd for HA.          │          │
│  └──────────────────────────────────────────────────────┘          │
│                                                                    │
│  INGESTION COMPLETE. Vectors persisted on ANF via Milvus.          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 2: Query (Live — user asks a question via Streamlit UI)

This is the real-time pipeline. A user types a question, and 6 specialized
agents collaborate to produce a compliance-reviewed investment memo.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          QUERY PIPELINE                            │
│                                                                    │
│  User types: "Compare AAPL and MSFT risk factors from 10-K"       │
│       │                                                            │
│       ▼                                                            │
│  ┌──────────────────────────────────────────────────────┐          │
│  │    STEP 1: NeMo Agent Toolkit Orchestrator            │          │
│  │                                                       │          │
│  │    nvidia-nat Runner loads workflow.yaml               │          │
│  │    Orchestrator agent (Chief Research Analyst) reads   │          │
│  │    the user query and decides which sub-agents to      │          │
│  │    invoke and in what order.                           │          │
│  │                                                       │          │
│  │    For "Compare AAPL and MSFT risk factors":           │          │
│  │      → Route to SEC Filing Agent (needs RAG)           │          │
│  │      → Route to Compliance Agent (review output)       │          │
│  │      → Route to Summarization Agent (format memo)      │          │
│  │                                                       │          │
│  │    STATUS: ⚠️  workflow.yaml defined, ui.py imports    │          │
│  │    nvidia_nat. Actual nvidia-nat package availability  │          │
│  │    and API (Runner, Config) needs confirmation from    │          │
│  │    NVIDIA. Falls back with error if not installed.     │          │
│  └──────────────────────────────┬────────────────────────┘          │
│                                 │                                   │
│         ┌───────────────────────┼───────────────────────┐          │
│         ▼                       ▼                       ▼          │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────────┐       │
│  │ SEC Filing   │  │ Earnings Agent   │  │ News Agent      │       │
│  │ Agent        │  │                  │  │                 │       │
│  │ Uses tool:   │  │ Uses tool:       │  │ Uses tool:      │       │
│  │ anf_milvus_  │  │ fetch_earnings_  │  │ fetch_market_   │       │
│  │ search       │  │ transcripts      │  │ news            │       │
│  │              │  │                  │  │                 │       │
│  │ STATUS: ✅   │  │ STATUS: ⚠️       │  │ STATUS: ⚠️      │       │
│  │ Full RAG     │  │ Mock data        │  │ Mock data       │       │
│  │ pipeline     │  │ (by design)      │  │ (by design)     │       │
│  └──────┬──────┘  └────────┬─────────┘  └────────┬────────┘       │
│         │                  │                      │                │
│         └──────────────────┼──────────────────────┘                │
│                            │                                       │
│                            ▼                                       │
│  ┌──────────────────────────────────────────────────────┐          │
│  │    STEP 2: RAG Retrieval (inside SEC Filing Agent)    │          │
│  │                                                       │          │
│  │    2a. Embed the question                             │          │
│  │    ┌─────────────────────────────────────┐            │          │
│  │    │ NIM: NV-EmbedQA-E5-v5               │            │          │
│  │    │ "Compare AAPL and MSFT risk factors" │            │          │
│  │    │  → [0.112, -0.034, 0.887, ...]       │            │          │
│  │    └─────────────────────┬───────────────┘            │          │
│  │                          │                            │          │
│  │    2b. Vector search in Milvus                        │          │
│  │    ┌─────────────────────────────────────┐            │          │
│  │    │ ANN search (IVF_FLAT, COSINE)        │            │          │
│  │    │ Over-fetch: 15 candidates (3x top_k) │            │          │
│  │    │ Returns chunks from AAPL + MSFT 10-Ks│            │          │
│  │    └─────────────────────┬───────────────┘            │          │
│  │                          │                            │          │
│  │    2c. Rerank with cross-encoder                      │          │
│  │    ┌─────────────────────────────────────┐            │          │
│  │    │ NIM: NV-RerankQA-Mistral-4B-v3       │            │          │
│  │    │ Reads each chunk alongside the query │            │          │
│  │    │ Scores: "Is this actually relevant?" │            │          │
│  │    │ Returns top 5 best passages           │            │          │
│  │    │                                      │            │          │
│  │    │ This catches false positives from     │            │          │
│  │    │ vector search — critical for legal    │            │          │
│  │    │ text where phrasing is similar but    │            │          │
│  │    │ meaning differs.                      │            │          │
│  │    └─────────────────────┬───────────────┘            │          │
│  │                          │                            │          │
│  │    STATUS: ✅ Fully implemented in                    │          │
│  │    anf_milvus_search.py with graceful fallback.       │          │
│  └──────────────────────────┬────────────────────────────┘          │
│                             │                                      │
│                             ▼                                      │
│  ┌──────────────────────────────────────────────────────┐          │
│  │    STEP 3: LLM Reasoning                              │          │
│  │                                                       │          │
│  │    NIM: Nemotron-Nano-9B-v2 (or Llama 3.1 8B)        │          │
│  │    ┌─────────────────────────────────────┐            │          │
│  │    │ Input: System prompt + retrieved      │            │          │
│  │    │ passages + user question              │            │          │
│  │    │                                      │            │          │
│  │    │ "Based on the following SEC filing    │            │          │
│  │    │  excerpts, compare AAPL and MSFT      │            │          │
│  │    │  risk factors..."                     │            │          │
│  │    │                                      │            │          │
│  │    │ Output: Structured analysis with      │            │          │
│  │    │ citations back to source documents.   │            │          │
│  │    └─────────────────────┬───────────────┘            │          │
│  │                          │                            │          │
│  │    STATUS: ✅ nim_client.chat_completion() implemented │          │
│  │    with retry logic. Model name configurable.         │          │
│  └──────────────────────────┬────────────────────────────┘          │
│                             │                                      │
│                             ▼                                      │
│  ┌──────────────────────────────────────────────────────┐          │
│  │    STEP 4: Compliance Review                          │          │
│  │                                                       │          │
│  │    Compliance Agent calls compliance_check()           │          │
│  │    ┌─────────────────────────────────────┐            │          │
│  │    │ Sends the draft to the LLM with a    │            │          │
│  │    │ FINRA/SEC compliance system prompt.   │            │          │
│  │    │                                      │            │          │
│  │    │ Checks for:                          │            │          │
│  │    │  - Unauthorized speculation           │            │          │
│  │    │  - Guarantees of future performance   │            │          │
│  │    │  - Implicit investment promises        │            │          │
│  │    │                                      │            │          │
│  │    │ Returns: PASSED or FAILED + fixes     │            │          │
│  │    └─────────────────────┬───────────────┘            │          │
│  │                          │                            │          │
│  │    STATUS: ✅ Implemented in compliance.py.           │          │
│  │    FUTURE: Add NeMo Guardrails NIMs for PII           │          │
│  │    detection, topic control, and jailbreak prevention. │          │
│  └──────────────────────────┬────────────────────────────┘          │
│                             │                                      │
│                             ▼                                      │
│  ┌──────────────────────────────────────────────────────┐          │
│  │    STEP 5: Summarization & Output                     │          │
│  │                                                       │          │
│  │    Summarization Agent formats the final memo:         │          │
│  │    ┌─────────────────────────────────────┐            │          │
│  │    │ - Executive Summary                  │            │          │
│  │    │ - Key Risks (per ticker)             │            │          │
│  │    │ - Sentiment Analysis                 │            │          │
│  │    │ - Sources Cited (ANF file paths)     │            │          │
│  │    └─────────────────────────────────────┘            │          │
│  │                                                       │          │
│  │    Rendered in Streamlit UI with agent trace.          │          │
│  └──────────────────────────────────────────────────────┘          │
│                                                                    │
│  RESPONSE DELIVERED TO USER.                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Map: What Runs Where

```
┌─────────────────────────────────────────────────────────────────┐
│                     AKS Cluster (East US 2)                     │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  GPU Node Pool (1x A100 80GB with time-slicing)           │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │  │
│  │  │ nim-llm      │ │ nim-embed   │ │ nim-rerank          │ │  │
│  │  │ Nemotron-    │ │ NV-EmbedQA  │ │ NV-RerankQA-        │ │  │
│  │  │ Nano-9B-v2   │ │ -E5-v5      │ │ Mistral-4B-v3       │ │  │
│  │  │ ~15GB VRAM   │ │ ~2GB VRAM   │ │ ~8GB VRAM           │ │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │  │
│  │  ┌─────────────────────┐                                  │  │
│  │  │ nim-retriever        │  (NV-Ingest / NeMo Retriever    │  │
│  │  │ NeMo Retriever Parse │   Parse — used at ingestion     │  │
│  │  │ ~10GB VRAM           │   time only, idle during query) │  │
│  │  └─────────────────────┘                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  System Node Pool (CPU — Standard_D4s_v3)                 │  │
│  │  ┌──────────┐ ┌──────────────┐ ┌────────────────────────┐│  │
│  │  │ Streamlit │ │ Milvus       │ │ Prometheus + Grafana   ││  │
│  │  │ UI + App  │ │ (cluster:    │ │ (monitoring)           ││  │
│  │  │ + nvidia- │ │  2 query,    │ │                        ││  │
│  │  │ nat agent │ │  2 data,     │ │                        ││  │
│  │  │ toolkit   │ │  1 index,    │ │                        ││  │
│  │  │           │ │  3 etcd)     │ │                        ││  │
│  │  └──────────┘ └──────────────┘ └────────────────────────┘│  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Azure NetApp Files (Standard 4TiB)                       │  │
│  │                                                           │  │
│  │  anf-data-pvc ─── Raw SEC PDFs + ingested documents       │  │
│  │  anf-milvus-pvc ─ Milvus vector data + WAL + metadata    │  │
│  │                                                           │  │
│  │  Dual access:                                             │  │
│  │   • NFS (POSIX mount) — standard file access              │  │
│  │   • S3 Object REST API — zero-ETL analytics access        │  │
│  │                                                           │  │
│  │  Protected by: ANF Snapshot Policy                        │  │
│  │   (6 hourly / 7 daily / 4 weekly / 12 monthly)           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Supporting Azure Services                                │  │
│  │   • Azure Key Vault — secrets (NGC key, AD creds, S3)     │  │
│  │   • ACR — app container image                             │  │
│  │   • Azure AD / Entra ID — user authentication (OIDC)      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## The 6 Agents (NeMo Agent Toolkit)

Defined in `app/workflow.yaml`, orchestrated by `nvidia-nat`:

| # | Agent | Role | Tool | What It Does |
|---|-------|------|------|-------------|
| 1 | **Orchestrator** | Chief Research Analyst | — | Reads user query, breaks it into sub-tasks, routes to the right agents |
| 2 | **SEC Filing Agent** | Fundamentals Analyst | `anf_milvus_search` | RAG retrieval from 10-K filings stored in Milvus on ANF |
| 3 | **Earnings Agent** | Sentiment Evaluator | `fetch_earnings_transcripts` | Analyzes earnings call Q&A sections (mock data for demo) |
| 4 | **News Agent** | Market Data Specialist | `fetch_market_news` | Fetches recent news events for a ticker (mock data for demo) |
| 5 | **Compliance Agent** | Regulatory Officer | `compliance_check` | FINRA/SEC review — flags unauthorized speculation or guarantees |
| 6 | **Summarization Agent** | Executive Editor | — | Formats final output as structured investment memo |

---

## Implementation Status

| Component | File(s) | Status | Notes |
|-----------|---------|--------|-------|
| PDF Download | `load-data.sh` | ✅ Ready | K8s Job pulls from SEC EDGAR |
| PDF Extraction (NV-Ingest) | `nim_client.extract_pdf()` | ⚠️ Stub | API shape guessed; NV-Ingest may need separate deployment |
| PDF Extraction (Fallback) | `ingest.py` → PyPDFLoader | ✅ Ready | Works without NV-Ingest; lower quality |
| Text Chunking | `ingest.py` | ✅ Ready | RecursiveCharacterTextSplitter 1000/100 |
| Embedding | `nim_client.get_embeddings()` | ✅ Ready | Needs NGC key + running NIM pod |
| Vector Storage | `ingest.py` → Milvus | ✅ Ready | IVF_FLAT index, ANF-backed PVC |
| Vector Search | `anf_milvus_search.py` | ✅ Ready | Full embed → search → rerank pipeline |
| Reranking | `nim_client.rerank()` | ✅ Ready | Graceful fallback if NIM unavailable |
| LLM Reasoning | `nim_client.chat_completion()` | ✅ Ready | Model name configurable |
| Compliance Check | `compliance.py` | ✅ Ready | LLM-based FINRA/SEC review |
| Agent Orchestration | `workflow.yaml` + `ui.py` | ⚠️ Depends | Needs `nvidia-nat` package confirmed |
| Market Data | `market_data.py` | ⚠️ Mock | Intentional — real APIs cost money |
| NeMo Guardrails | — | ❌ Not yet | PII detection, topic control, jailbreak |
| Azure AD Auth | `ui.py` | ✅ Ready | AUTH_ENABLED toggle |
| Monitoring | Prometheus + Grafana | ✅ Ready | Custom 16-panel dashboard |

---

## Future Additions (Post-NGC-Key)

1. **NeMo Guardrails NIMs** — add content safety, topic control, and PII detection
   as a pre/post filter around the LLM. Especially important for financial compliance.
2. **NV-Ingest full deployment** — replace the single `extract_pdf()` call with
   the proper multi-container NV-Ingest pipeline for production-grade PDF extraction.
3. **Real market data APIs** — swap mock data with Alpha Vantage, Yahoo Finance,
   or Polygon.io when budget allows.
4. **Nemotron-Nano-9B-v2** — swap Llama 3.1 8B for NVIDIA's own model with 128K
   context window and built-in reasoning traces.
