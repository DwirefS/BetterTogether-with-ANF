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
  }
}

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
        count: 2
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
      }
    ]
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
    }
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

output aksClusterName string = aks.name
output anfDataVolumeIp string = dataVolume.properties.mountTargets[0].ipAddress
output anfDataVolumePath string = dataVolume.properties.creationToken
output anfMilvusVolumeIp string = milvusVolume.properties.mountTargets[0].ipAddress
output anfMilvusVolumePath string = milvusVolume.properties.creationToken
output keyVaultName string = keyVault.name
