# Project AlphaAgent Makefile (Enterprise Stack)

# Load environment variables safely
include .env
export $(shell sed 's/=.*//' .env)

# Required arguments
NGC_API_KEY ?= ""

.PHONY: help deploy load-data logs status destroy ssh dashboard

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

deploy: ## Deploy full AKS enterprise stack (Bicep + Helm + App)
	@if [ -z "$(NGC_API_KEY)" ]; then echo "Error: NGC_API_KEY is required. Usage: make deploy NGC_API_KEY=..."; exit 1; fi
	./scripts/deploy.sh "$(NGC_API_KEY)"

status: ## Show cluster status, ingress endpoints, and K8s node health
	./scripts/status.sh

load-data: ## Download SEC filings and ingest into Milvus on Azure NetApp Files
	./scripts/load-data.sh

logs: ## Tail logs from the Streamlit UI and NeMo Agent pod
	./scripts/logs.sh

dashboard: ## Open AKS dashboard / Kubeview (if installed)
	echo "Use 'az aks browse' or standard kubectl commands to view cluster state."

destroy: ## Safely destroy all Azure resources
	./scripts/destroy.sh
