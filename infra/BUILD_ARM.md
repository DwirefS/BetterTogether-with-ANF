# Regenerating ARM Template from Bicep

The `main.json` ARM template must be regenerated after modifying `main.bicep`.

## When to rebuild

Rebuild after any change to `main.bicep` — especially after adding:
- AKS cluster autoscaler (`enableAutoScaling`, `minCount`, `maxCount`)
- ANF snapshot policy resource
- Key Vault CSI driver AKS addon (`azureKeyvaultSecretsProvider`)
- New parameters (`gpuNodeMinCount`, `gpuNodeMaxCount`)

## How to rebuild

### Option 1: Azure Cloud Shell (recommended)
```bash
# Upload main.bicep to Cloud Shell, then:
az bicep build --file main.bicep --outfile main.json
```

### Option 2: Local machine with az CLI
```bash
# Install Bicep if needed
az bicep install

# Build
az bicep build --file infra/main.bicep --outfile infra/main.json
```

### Option 3: Makefile shortcut
```bash
make bicep-build
```

## Important

`deploy.sh` uses `main.json` (not `main.bicep`) to avoid requiring Bicep CLI on the deployment machine. Always commit the updated `main.json` alongside `main.bicep` changes.
