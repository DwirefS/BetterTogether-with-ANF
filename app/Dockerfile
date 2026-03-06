FROM python:3.11-slim

WORKDIR /app

# Install system deps for PDF/XLSX generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Attempt nvidia-nat install (requires NGC private PyPI index).
# This is non-fatal — the app has a graceful ImportError fallback in ui.py.
ARG NGC_PYPI_URL=""
RUN if [ -n "$NGC_PYPI_URL" ]; then \
      pip install --no-cache-dir "nvidia-nat>=0.3.0" --extra-index-url "$NGC_PYPI_URL" || \
      echo "WARNING: nvidia-nat install failed. Agent orchestration will be unavailable."; \
    else \
      echo "INFO: NGC_PYPI_URL not set. Skipping nvidia-nat install."; \
    fi

COPY . .

# Default: run Streamlit
CMD ["streamlit", "run", "ui.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
