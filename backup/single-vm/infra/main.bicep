// ============================================================================
// AlphaAgent — Azure Infrastructure (VNet + ANF + GPU VM)
// ============================================================================
// Deploys: VNet, delegated subnet for ANF, ANF account/pool/volume (NFSv4.1),
//          GPU VM with NVIDIA GPU driver extension, NSG rules, cloud-init.
// ============================================================================

param prefix string
param location string = resourceGroup().location
param adminUsername string
@secure()
param sshPublicKey string

param vmSize string = 'Standard_NC4as_T4_v3'

// Networking
param vnetAddressPrefix string = '10.10.0.0/16'
param vmSubnetPrefix string = '10.10.1.0/24'
param anfSubnetPrefix string = '10.10.2.0/24'

// NSG inbound (demo defaults — restrict for production)
param allowedSshCidr string = '0.0.0.0/0'
param allowedUiCidr string = '0.0.0.0/0'

// ANF sizing
@allowed([
  'Standard'
  'Premium'
  'Ultra'
  'StandardZRS'
])
param anfServiceLevel string = 'Premium'
param anfPoolSizeTiB int = 4
param anfVolumeSizeGiB int = 100

// Image
param ubuntuSku string = '22_04-lts-gen2'

// ---- Derived names ----
var vnetName = '${prefix}-vnet'
var vmSubnetName = 'vm'
var anfSubnetName = 'anf'
var nsgName = '${prefix}-nsg'
var pipName = '${prefix}-pip'
var nicName = '${prefix}-nic'
var vmName = '${prefix}-gpuvm'

// ANF names must conform to length/charset constraints
var anfAccountName = toLower(replace('${prefix}anfacct', '-', ''))
var anfPoolName = 'pool1'
var anfVolumeName = 'vol1'
var anfCreationToken = 'cmdata' // mount path: <mountIp>:/cmdata

// ---- Network Security Group ----
resource nsg 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: nsgName
  location: location
  properties: {
    securityRules: [
      {
        name: 'Allow-SSH'
        properties: {
          priority: 100
          protocol: 'Tcp'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: allowedSshCidr
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '22'
        }
      }
      {
        name: 'Allow-Streamlit-UI'
        properties: {
          priority: 110
          protocol: 'Tcp'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: allowedUiCidr
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '8501'
        }
      }
    ]
  }
}

// ---- Virtual Network with VM + ANF subnets ----
resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: vmSubnetName
        properties: {
          addressPrefix: vmSubnetPrefix
          networkSecurityGroup: {
            id: nsg.id
          }
        }
      }
      {
        name: anfSubnetName
        properties: {
          addressPrefix: anfSubnetPrefix
          delegations: [
            {
              name: 'delegation'
              properties: {
                serviceName: 'Microsoft.NetApp/volumes'
              }
            }
          ]
        }
      }
    ]
  }
}

// ---- Public IP ----
resource pip 'Microsoft.Network/publicIPAddresses@2023-11-01' = {
  name: pipName
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
    dnsSettings: {
      domainNameLabel: toLower('${uniqueString(resourceGroup().id, prefix)}')
    }
  }
}

// ---- NIC ----
resource nic 'Microsoft.Network/networkInterfaces@2023-11-01' = {
  name: nicName
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          publicIPAddress: {
            id: pip.id
          }
          subnet: {
            id: resourceId('Microsoft.Network/virtualNetworks/subnets', vnetName, vmSubnetName)
          }
        }
      }
    ]
  }
}

// ---- GPU Virtual Machine ----
var cloudInit = base64(loadTextContent('cloud-init.yaml'))

resource vm 'Microsoft.Compute/virtualMachines@2024-03-01' = {
  name: vmName
  location: location
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    osProfile: {
      computerName: vmName
      adminUsername: adminUsername
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: sshPublicKey
            }
          ]
        }
      }
      customData: cloudInit
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: '0001-com-ubuntu-server-jammy'
        sku: ubuntuSku
        version: 'latest'
      }
      osDisk: {
        createOption: 'FromImage'
        diskSizeGB: 256
        managedDisk: {
          storageAccountType: 'Premium_LRS'
        }
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: nic.id
        }
      ]
    }
  }
}

// ---- NVIDIA GPU Driver Extension ----
// Installs NVIDIA GPU drivers on Linux N-series VMs.
// Reference: https://learn.microsoft.com/azure/virtual-machines/extensions/hpccompute-gpu-linux
resource nvidiaDriver 'Microsoft.Compute/virtualMachines/extensions@2022-11-01' = {
  name: '${vmName}/NvidiaGpuDriverLinux'
  location: location
  dependsOn: [
    vm
  ]
  properties: {
    publisher: 'Microsoft.HpcCompute'
    type: 'NvidiaGpuDriverLinux'
    typeHandlerVersion: '1.11'
    autoUpgradeMinorVersion: true
    settings: {}
  }
}

// ---- Azure NetApp Files: Account → Pool → Volume (NFSv4.1) ----
resource anfAccount 'Microsoft.NetApp/netAppAccounts@2024-07-01' = {
  name: anfAccountName
  location: location
  properties: {
    activeDirectories: []
  }
}

resource anfPool 'Microsoft.NetApp/netAppAccounts/capacityPools@2024-07-01' = {
  name: anfPoolName
  parent: anfAccount
  location: location
  properties: {
    serviceLevel: anfServiceLevel
    size: int(anfPoolSizeTiB) * 1099511627776 // Convert TiB to bytes
  }
}

resource anfVolume 'Microsoft.NetApp/netAppAccounts/capacityPools/volumes@2024-07-01' = {
  name: anfVolumeName
  parent: anfPool
  location: location
  properties: {
    creationToken: anfCreationToken
    serviceLevel: anfServiceLevel
    usageThreshold: int(anfVolumeSizeGiB) * 1073741824 // Convert GiB to bytes
    protocolTypes: [
      'NFSv4.1'
    ]
    subnetId: resourceId('Microsoft.Network/virtualNetworks/subnets', vnetName, anfSubnetName)
    snapshotDirectoryVisible: true
    exportPolicy: {
      rules: [
        {
          ruleIndex: 1
          allowedClients: vmSubnetPrefix
          unixReadOnly: false
          unixReadWrite: true
          hasRootAccess: true
          cifs: false
          nfsv3: false
          nfsv41: true
        }
      ]
    }
  }
}

// ---- Outputs ----
output adminUsername string = adminUsername
output vmName string = vmName
output vmPublicIp string = pip.properties.ipAddress
output vmFqdn string = pip.properties.dnsSettings.fqdn
output anfExportPath string = anfCreationToken
output anfMountIp string = anfVolume.properties.mountTargets[0].ipAddress
output anfMountCommand string = 'sudo mount -t nfs -o vers=4.1 ${anfVolume.properties.mountTargets[0].ipAddress}:/${anfCreationToken} /mnt/anf'
