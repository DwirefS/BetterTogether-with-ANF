#!/bin/bash
# AlphaAgent Log Viewer — Tails logs from the Streamlit app and NIM pods.

NAMESPACE="finserv-ai"

echo "Tailing AlphaAgent application logs (Ctrl+C to stop)..."
echo ""

# Find the app pod
APP_POD=$(kubectl get pods -n "$NAMESPACE" -l app=alpha-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -n "$APP_POD" ]; then
    echo "--- Streamlit App Pod: $APP_POD ---"
    kubectl logs -n "$NAMESPACE" "$APP_POD" --tail=100 -f
else
    echo "⚠️  No alpha-agent pod found. Showing all pods in $NAMESPACE:"
    kubectl get pods -n "$NAMESPACE"
    echo ""
    echo "To tail a specific pod: kubectl logs -n $NAMESPACE <pod-name> -f"
fi
