# Project AlphaAgent Makefile (Enterprise Stack)

# Load environment variables safely
-include .env
export $(shell [ -f .env ] && sed 's/=.*//' .env)

# Required arguments
NGC_API_KEY ?= ""

.PHONY: help deploy load-data logs status destroy monitoring port-forward bicep-build lint

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

deploy: ## Deploy full AKS enterprise stack end-to-end (Infra + Helm + NIMs + Monitoring + App + Data)
	@if [ -z "$(NGC_API_KEY)" ]; then echo "Error: NGC_API_KEY is required. Usage: make deploy NGC_API_KEY=..."; exit 1; fi
	chmod +x scripts/*.sh
	./scripts/deploy.sh "$(NGC_API_KEY)"

status: ## Show cluster status, NIM health, reranker integration, monitoring, ANF snapshots
	@chmod +x scripts/status.sh 2>/dev/null || true
	./scripts/status.sh

load-data: ## Download SEC filings and ingest into Milvus on Azure NetApp Files
	@chmod +x scripts/load-data.sh 2>/dev/null || true
	./scripts/load-data.sh

logs: ## Tail logs from the Streamlit UI and NeMo Agent pod
	@chmod +x scripts/logs.sh 2>/dev/null || true
	./scripts/logs.sh

monitoring: ## Port-forward Grafana dashboard to localhost:3000
	@echo "Opening Grafana dashboard (admin / AlphaAgent-Demo-2024)..."
	kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80

port-forward: ## Port-forward Streamlit UI to localhost:8501 (alternative to LoadBalancer)
	@echo "Forwarding Streamlit UI to http://localhost:8501 ..."
	kubectl port-forward -n finserv-ai svc/streamlit-ui 8501:8501

bicep-build: ## Compile Bicep → ARM JSON (requires az bicep CLI)
	@echo "Compiling infra/main.bicep → infra/main.json ..."
	az bicep build --file infra/main.bicep --outfile infra/main.json
	@echo "ARM template generated: infra/main.json"

destroy: ## Safely destroy all Azure resources (prompts for confirmation)
	@chmod +x scripts/destroy.sh 2>/dev/null || true
	./scripts/destroy.sh

lint: ## Lint Python code with flake8
	@echo "Linting app/ ..."
	flake8 app/ --max-line-length=120 --ignore=E501,W503 || true
