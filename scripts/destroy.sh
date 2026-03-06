#!/bin/bash
set -e

# AlphaAgent Enterprise Teardown Script
# Safely destroys the AKS cluster, VNet, and Azure NetApp Files resources.

# [ORIGINAL] default was "DNvidiaAgent"
RESOURCE_GROUP=${RG_NAME:-"DNvidiaANF"}

echo "⚠️  WARNING: You are about to destroy the entire AlphaAgent enterprise deployment."
echo "This will delete the AKS cluster, Azure NetApp Files volumes, and all data."
echo "Resource Group: $RESOURCE_GROUP"
read -p "Are you sure? (y/N): " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Teardown aborted."
    exit 0
fi

echo "🗑️  Destroying resource group $RESOURCE_GROUP... (This may take roughly 10-15 minutes)"
az group delete --name $RESOURCE_GROUP --yes --no-wait

echo "✅ Deletion initiated in the background. You can check status via Azure Portal."
