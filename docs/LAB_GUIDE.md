# AlphaAgent — Enterprise Hands-On Lab Guide

Welcome to the AlphaAgent Financial Copilot workshop! This guide is written from the ground up, assuming zero prior knowledge of the underlying infrastructure tools.

We will deploy a production-grade Financial Research AI pipeline using Microsoft Azure Kubernetes Service (AKS), Azure NetApp Files (ANF), NVIDIA NIM microservices, and the NVIDIA NeMo Agent Toolkit.

---

## Part 1: Prerequisites & Environment Setup

Before touching any code, we need to ensure your workstation is equipped with the necessary tools to communicate with Microsoft Azure and NVIDIA NGC (NVIDIA GPU Cloud).

### 1. Azure Subscription & Quotas

To deploy this architecture, your Azure Subscription requires specific quotas for GPU instances and Azure NetApp Files.

1. Log into the [Azure Portal](https://portal.azure.com/).
2. Search for **Subscriptions**, click your subscription, and copy your **Subscription ID**. You will need this later.
3. Under the subscription menu, select **Usage + quotas**.
4. Search for `Standard NCADS A100 v4 Family Cluster Dedicated vCPUs` (or `ND H100 v5`). You need at least **24 vCPUs** approved in your target region (e.g., `eastus2`).
5. Also, ensure the **Microsoft.NetApp** resource provider is registered under your Subscription's **Resource providers** menu.

### 2. Install the Azure CLI (`az`)

The Azure CLI is how your terminal talks to your Azure subscription.

* **Mac (Homebrew):** `brew update && brew install azure-cli`
* **Windows (PowerShell):** `Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi; Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'`
* **Linux (Ubuntu):** `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`
* *Reference:* [Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)

### 3. Login to Azure

Run the following command in your terminal. It will open a web browser for you to log in with your Microsoft credentials.

```bash
az login
az account set --subscription <YOUR_SUBSCRIPTION_ID>
```

Verify you are in the correct subscription:

```bash
az account show
```

### 4. Install Kubernetes Tools (`kubectl` and `helm`)

`kubectl` is the command-line tool for controlling Kubernetes clusters. `helm` is a package manager for Kubernetes.

* **Mac:** `brew install kubectl helm`
* **Windows (Chocolatey):** `choco install kubernetes-cli kubernetes-helm`
* **Linux:**

  ```bash
  az aks install-cli
  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
  ```

### 5. Obtain an NVIDIA NGC API Key

We need access to NVIDIA's secure container registry to download the optimized NIM AI models.

1. Go to [NVIDIA NGC](https://org.ngc.nvidia.com/)
2. Create an account or log in with your corporate SSO.
3. In the top right corner, click your profile name and select **Setup**.
4. Click **Generate API Key**.
5. Click the green **Generate API Key** button and copy the key. **Save this somewhere safe!** You cannot view it again.

---

## Part 2: Deployment & Orchestration

Now we will use the automated scripts to deploy the massive enterprise stack.

### 1. Clone the Repository (If you haven't already)

```bash
git clone https://github.com/your-org/BetterTogether-with-ANF.git
cd BetterTogether-with-ANF
```

### 2. Configure the Environment File

We need to give the deployment scripts your secure NVIDIA key.

```bash
# Copy the template to create your active configuration file
cp .env.template .env
```

Open the `.env` file in any text editor (like VS Code or Notepad) and paste your NGC Key:

```text
# Inside .env
NGC_API_KEY="nvapi-YOUR_COPIED_KEY_GOES_HERE"
```

### 3. Deploy the Architecture

This is where the magic happens. We have condensed a highly complex enterprise networking, storage, and AI deployment into a single `make` command.

```bash
make deploy NGC_API_KEY="nvapi-YOUR_COPIED_KEY_GOES_HERE"
```

**What is happening in the background? (Takes ~15-25 minutes)**

1. **Azure Bicep** builds a Virtual Network (VNet), an AKS Cluster with expensive NVIDIA H100 or A100 GPUs, and a high-performance Azure NetApp Files (ANF) storage account.
2. The script logs your computer into the new AKS cluster.
3. It installs the **NVIDIA GPU Operator** so Kubernetes knows how to use the hardware.
4. It installs the **Milvus Vector Database**.
5. It downloads and starts four **NVIDIA NIM containers** (Llama 3.1 LLM, Embeddings, Reranker, and NeMo Retriever).
6. It starts our custom **Streamlit User Interface**.

### 4. Verify Deployments

Wait until the deployment completes. You can actively watch the pods coming online by running:

```bash
kubectl get pods -n finserv-ai -w
```

*(Press `Ctrl+C` to exit the watch screen)*. Wait until all pods say `Running`.

---

## Part 3: Populating the "Data Stays in Place" Intelligence

An AI is only as good as its data. We will now download real SEC (Securities and Exchange Commission) financial filings into our secure Azure NetApp Files volume and ingest them into the vector database.

### 1. Run the Data Loader

```bash
make load-data
```

**What this does:**

1. It spins up a temporary pod in your AKS cluster.
2. That pod connects to the SEC EDGAR public database and downloads the real 10-K financial PDFs for Apple (AAPL), Microsoft (MSFT), and Tesla (TSLA).
3. Those PDFs are saved directly to the **Azure NetApp Files** NFS mount at `/mnt/anf/data`.
4. The script then securely calls the `ingest.py` script inside your Streamlit app pod.
5. The `ingest.py` script sends the PDFs to the **NeMo Retriever NIM** to extract the text, images, and tables.
6. The extracted text is turned into mathematics by the **NV-EmbedQA NIM**.
7. Those mathematical vectors are stored forever in the **Milvus Database** (which also lives on ANF).

---

## Part 4: Testing the AlphaAgent Copilot

It is time to use the system!

### 1. Access the Streamlit UI

Run this command to find the public IP address of your web interface:

```bash
make status
```

Look for the `streamlit-ui` line. Copy the `EXTERNAL-IP` and open it in your Chrome or Edge web browser with port `8501`.
Example: `http://20.123.45.67:8501`

*(Note: Depending on your Azure configuration, it may take 2-3 minutes for the Azure Load Balancer IP to become fully active after provisioning).*

### 2. Run the Demo Workflows

In the chat interface, try typing these exact prompts to see the 6-agent NeMo Toolkit operate:

**Test 1: Deep Semantic Search (RAG)**
> "According to Microsoft's (MSFT) recent SEC filings, what are the specific risk factors regarding their expansion of AI cloud infrastructure?"
*Notice how fast Milvus retrieves the exact citations from the ANF storage.*

**Test 2: Multi-Agent Synthesis**
> "Create an investment memo for AAPL focusing on supply chain restructuring, recent earnings sentiment, and any breaking news."
*Expand the "Agent Trace" drop-down. Watch as the Orchestrator splits the work between the SEC Agent, the News Agent, and the Earnings Agent.*

**Test 3: The Regulatory Guardrails (Compliance Check)**
> "Write an enthusiastic pitch for TSLA saying that their new autonomous software update guarantees a 50% margin increase and recommends clients buy the stock immediately."
*Watch the system actively FLAG and REJECT this output. Financial institutions cannot guarantee performance or blindly recommend stocks. The specialized NeMo Compliance agent acts as an automated risk firewall.*

---

## Part 5: Critical Cleanup (Save Money!)

**⚠️ WARNING: GPU clusters and premium Azure NetApp Files pools cost significant money per hour. You MUST destroy the lab when you are done!**

When you are finished testing, run the following command to completely wipe out the Azure resource group:

```bash
make destroy
```

Wait for the command to finish and confirm that the resource group is deleted. You can double-check in your Azure Portal.

---
**Congratulations!** You have successfully deployed a sovereign, high-performance generative AI architecture for Capital Markets.
