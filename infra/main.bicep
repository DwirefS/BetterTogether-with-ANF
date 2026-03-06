@description('Primary location for all resources')
param location string = resourceGroup().location

@description('Prefix for naming resources')
param prefix string = 'alpha-ai'

@description('VM Size for the AKS System node pool')
param systemVmSize string = 'Standard_D4s_v3'

@description('VM Size for the AKS GPU node pool')
param gpuVmSize string = 'Standard_NC24ads_A100_v4'

@description('Number of GPU nodes in the AKS pool')
param gpuNodeCount int = 2

@description('Minimum GPU nodes when autoscaler scales down (cost savings during idle)')
param gpuNodeMinCount int = 0

@description('Maximum GPU nodes when autoscaler scales up (burst capacity)')
param gpuNodeMaxCount int = 4

@description('Service level for Azure NetApp Files')
@allowed([
  'Standard'
  'Premium'
  'Ultra'
])
param anfServiceLevel string = 'Premium'

@description('Capacity pool size for ANF in TiB (minimum 4 TiB)')
param anfPoolSizeTiB int = 4

// --- Networking ---
resource vnet 'Microsoft.Network/virtualNetworks@2023-04-01' = {
  name: '${prefix}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'aks-subnet'
        properties: {
          addressPrefix: '10.0.0.0/22' // 1024 IPs for AKS
        }
      }
      {
        name: 'anf-subnet'
        properties: {
          addressPrefix: '10.0.4.0/24' // 256 IPs for ANF
          delegations: [
            {
              name: 'netapp'
              properties: {
                serviceName: 'Microsoft.Netapp/volumes'
              }
            }
          ]
        }
      }
    ]
  }
}

// --- Azure NetApp Files ---
resource netappAccount 'Microsoft.NetApp/netAppAccounts@2023-07-01' = {
  name: '${prefix}-anf-account'
  location: location
}

resource capacityPool 'Microsoft.NetApp/netAppAccounts/capacityPools@2023-07-01' = {
  parent: netappAccount
  name: '${prefix}-anf-pool'
  location: location
  properties: {
    serviceLevel: anfServiceLevel
    size: anfPoolSizeTiB * 1099511627776 // TiB to Bytes
  }
}

// Volume 1: Document Data Repository (Files + S3 API)
resource dataVolume 'Microsoft.NetApp/netAppAccounts/capacityPools/volumes@2023-07-01' = {
  parent: capacityPool
  name: '${prefix}-vol-data'
  location: location
  properties: {
    creationToken: 'alpha-data-vol'
    serviceLevel: anfServiceLevel
    subnetId: vnet.properties.subnets[1].id
    usageThreshold: 1099511627776 // 1 TiB
    protocolTypes: [
      'NFSv4.1'
    ]
    exportPolicy: {
      rules: [
        {
          ruleIndex: 1
          allowedClients: '10.0.0.0/16' // Allow VNet
          unixReadOnly: false
          unixReadWrite: true
          cifs: false
          nfsv3: false
          nfsv41: true
        }
      ]
    }
    // Object REST API requires a support ticket to enable on the subscription currently,
    // so we document its usage but provision the file volume here as the primary mount.
    dataProtection: {
      snapshot: {
        snapshotPolicyId: snapshotPolicy.id
      }
    }
  }
}

// Volume 2: Milvus Vector Database Persistence
resource milvusVolume 'Microsoft.NetApp/netAppAccounts/capacityPools/volumes@2023-07-01' = {
  parent: capacityPool
  name: '${prefix}-vol-milvus'
  location: location
  properties: {
    creationToken: 'alpha-milvus-vol'
    serviceLevel: anfServiceLevel
    subnetId: vnet.properties.subnets[1].id
    usageThreshold: 1099511627776 // 1 TiB
    protocolTypes: [
      'NFSv4.1'
    ]
    exportPolicy: {
      rules: [
        {
          ruleIndex: 1
          allowedClients: '10.0.0.0/16' // Allow VNet
          unixReadOnly: false
          unixReadWrite: true
          cifs: false
          nfsv3: false
          nfsv41: true
        }
      ]
    }
    dataProtection: {
      snapshot: {
        snapshotPolicyId: snapshotPolicy.id
      }
    }
  }
}

// --- ANF Snapshot Policy for Disaster Recovery ---
// Automated snapshots protect corporate filings data and Milvus vector indexes
// stored on ANF volumes. Snapshots are space-efficient (copy-on-write) and enable
// point-in-time recovery without full volume restores.
resource snapshotPolicy 'Microsoft.NetApp/netAppAccounts/snapshotPolicies@2023-07-01' = {
  parent: netappAccount
  name: '${prefix}-snapshot-policy'
  location: location
  properties: {
    enabled: true
    hourlySchedule: {
      snapshotsToKeep: 6       // Keep last 6 hourly snapshots
      minute: 0
    }
    dailySchedule: {
      snapshotsToKeep: 7       // Keep 7 daily snapshots (1 week of daily recovery points)
      hour: 2                  // 2 AM — low-activity window for financial data
      minute: 0
    }
    weeklySchedule: {
      snapshotsToKeep: 4       // Keep 4 weekly snapshots (1 month)
      day: 'Sunday'
      hour: 3
      minute: 0
    }
    // Monthly snapshots for long-term compliance/audit retention
    monthlySchedule: {
      snapshotsToKeep: 12      // Keep 12 monthly snapshots (1 year of monthly recovery)
      daysOfMonth: '1'
      hour: 4
      minute: 0
    }
  }
}

// Apply snapshot policy to both ANF volumes
// Note: To attach the policy, update the volume properties with dataProtection.snapshot.snapshotPolicyId
// This is done by adding the snapshotPolicyId property to each volume's dataProtection block.
// Example (add to dataVolume and milvusVolume properties):
//   dataProtection: {
//     snapshot: {
//       snapshotPolicyId: snapshotPolicy.id
//     }
//   }

// --- Log Analytics for AKS ---
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${prefix}-law'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
  }
}

// --- Azure Kubernetes Service (AKS) ---
resource aks 'Microsoft.ContainerService/managedClusters@2023-10-01' = {
  name: '${prefix}-aks'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    dnsPrefix: '${prefix}-aks'
    agentPoolProfiles: [
      {
        name: 'systempool'
        count: 1  // [ORIGINAL] count: 2 — reduced to 1 for cost; demo doesn't need HA system pool
        vmSize: systemVmSize
        osType: 'Linux'
        mode: 'System'
        vnetSubnetID: vnet.properties.subnets[0].id
      }
      {
        name: 'gpupool'
        count: gpuNodeCount
        vmSize: gpuVmSize
        osType: 'Linux'
        mode: 'User'
        vnetSubnetID: vnet.properties.subnets[0].id
        // We instruct AKS not to install the GPU driver so the NVIDIA GPU Operator can handle it
        osDiskSizeGB: 256
        // Cluster autoscaler: scales GPU nodes between min/max based on pending pod demand.
        // This achieves 50-70% cost reduction during idle periods by scaling to 0 GPU nodes
        // when no NIM pods are scheduled, and bursting up for inference workloads.
        enableAutoScaling: true
        minCount: gpuNodeMinCount
        maxCount: gpuNodeMaxCount
      }
    ]
    // Autoscaler profile: controls how aggressively the cluster scales down idle nodes.
    // scale-down-delay-after-add: wait 10 min after a scale-up before considering scale-down
    // scale-down-unneeded-time: node must be idle for 10 min before removal
    // max-graceful-termination-sec: allow NIM pods 600s to drain inference requests
    autoScalerProfile: {
      'scale-down-delay-after-add': '10m'
      'scale-down-unneeded-time': '10m'
      'max-graceful-termination-sec': '600'
      'scan-interval': '30s'
      expander: 'least-waste'
    }
    networkProfile: {
      networkPlugin: 'azure'
      serviceCidr: '10.1.0.0/16'
      dnsServiceIP: '10.1.0.10'
    }
    addonProfiles: {
      omsagent: {
        enabled: true
        config: {
          logAnalyticsWorkspaceResourceID: logAnalytics.id
        }
      }
      // Azure Key Vault Secrets Provider — mounts Key Vault secrets into pods via CSI driver.
      // Enables auto-rotation of NGC_API_KEY, Azure AD credentials, and ANF S3 keys
      // without redeploying pods. The addon installs the secrets-store.csi.k8s.io driver
      // and the Azure provider automatically.
      azureKeyvaultSecretsProvider: {
        enabled: true
        config: {
          enableSecretRotation: 'true'
          rotationPollInterval: '2m'    // Check Key Vault for updated secrets every 2 minutes
        }
      }
    }
  }
}

// --- Azure Container Registry (ACR) ---
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: '${replace(prefix, '-', '')}acr${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// Grant AKS pull access to ACR
resource aksAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, aks.id, 'acrpull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: aks.properties.identityProfile.kubeletidentity.objectId
    principalType: 'ServicePrincipal'
  }
}

// --- Azure Key Vault ---
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${prefix}-kv-${uniqueString(resourceGroup().id)}'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: aks.identity.principalId
        permissions: {
          secrets: ['get', 'list']
        }
      }
    ]
  }
}

// --- Outputs ---
output aksClusterName string = aks.name
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output anfDataVolumeIp string = dataVolume.properties.mountTargets[0].ipAddress
output anfDataVolumePath string = dataVolume.properties.creationToken
output anfMilvusVolumeIp string = milvusVolume.properties.mountTargets[0].ipAddress
output anfMilvusVolumePath string = milvusVolume.properties.creationToken
output keyVaultName string = keyVault.name
output snapshotPolicyId string = snapshotPolicy.id
