# Talk Track: The GTC Booth Demo

**Duration:** 3-4 Minutes
**Audience:** Financial Institutions, Capital Markets IT, Enterprise Architects

## 1. The Hook (30 seconds)
>
> "Welcome. What you're looking at is the AlphaAgent Financial Copilot. Generative AI holds massive promise for capital markets, but the reality is that financial data—SEC filings, risk reports, trade confirmations—is trapped in complex PDFs sitting on enterprise file shares. Moving that data to the cloud or duplicating it to object stores for AI is expensive, slow, and a compliance nightmare. Today, we're going to show you how Microsoft Azure, NVIDIA, and NetApp solve this without moving a single byte of data."

## 2. Setting the Stage (45 seconds)
>
> "This entire environment is running live on Microsoft Azure using Azure Kubernetes Service (AKS) with NVIDIA H100 GPUs.
>
> Underneath it all is **Azure NetApp Files**. It's providing our enterprise data layer. Here's the magic: ANF offers file and object duality. That means your existing legacy Windows and Linux applications can write SEC filings to an NFS or SMB share, and the AI Pipeline reads those *exact same files* immediately using an S3-compatible Object REST API. No ETL, no duplication. Data stays in place."

## 3. The Extraction Challenge (45 seconds)
>
> *(Point to the Document ingestion phase on the architecture diagram)*
> "Standard OCR fails completely on financial documents. A 10-K filing has dense tables, footnotes, and charts.
>
> That's why we use **NVIDIA NeMo Retriever**. Running as a NIM microservice on our AKS cluster, it intelligently extracts structure from PDFs—understanding tables and images. We then embed that text using NVIDIA's NV-EmbedQA model, and store the vectors in Milvus. And where does Milvus persist its data? Right back on high-performance Azure NetApp Files."

## 4. The Agentic Query (60 seconds)
>
> *(Type query into the Streamlit UI: "Compare AAPL and MSFT risk factors from their latest 10-K")*
> "Now let's ask a complex question. Notice what happens under the hood. We aren't just sending a prompt to an LLM. We are using the **NVIDIA NeMo Agent Toolkit**.
>
> The Orchestrator agent breaks down the query. It sends a request to the SEC Filing Agent, which hits our Milvus database. But what's crucial for finance is compliance. Notice the **Compliance Agent** kicks in right here. It uses a Nemotron reasoning model to check the drafted response against built-in FINRA and SEC guardrails. Only when it passes does the Summarization agent finalize the report."

## 5. The Close (30 seconds)
>
> "What you just saw isn't a science project. This is a production-grade blueprint. Data sovereignty, enterprise governance, and the deepest vertical AI models on the market.
> **Azure NetApp Files for the data estate. NVIDIA AI for the intelligence. Azure for the cloud scale. Better Together.**"
