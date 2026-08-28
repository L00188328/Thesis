targetScope = 'resourceGroup'

@description('Azure region for this AKS cluster.')
param location string

@description('AKS cluster name.')
param clusterName string

@allowed([
  'Free'
  'Standard'
])
param aksTier string = 'Free'

param kubernetesVersion string
param systemPoolVmSize string = 'Standard_B2s'
param systemPoolCount int = 1
param systemPoolZones array = []
param appPools array
param tags object = {}

resource cluster 'Microsoft.ContainerService/managedClusters@2025-01-01' = {
  name: clusterName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Base'
    tier: aksTier
  }
  properties: {
    dnsPrefix: clusterName
    kubernetesVersion: kubernetesVersion
    enableRBAC: true
    disableLocalAccounts: false
    agentPoolProfiles: [
      {
        name: 'system'
        count: systemPoolCount
        vmSize: systemPoolVmSize
        osType: 'Linux'
        osSKU: 'Ubuntu'
        mode: 'System'
        type: 'VirtualMachineScaleSets'
        availabilityZones: systemPoolZones
        enableAutoScaling: false
        nodeLabels: {
          workload: 'system'
        }
      }
    ]
    networkProfile: {
      networkPlugin: 'azure'
      networkPluginMode: 'overlay'
      networkPolicy: 'azure'
      loadBalancerSku: 'standard'
      outboundType: 'loadBalancer'
    }
    autoUpgradeProfile: {
      upgradeChannel: 'none'
      nodeOSUpgradeChannel: 'None'
    }
    addonProfiles: {
      azureKeyvaultSecretsProvider: {
        enabled: false
      }
    }
  }
}

resource applicationPools 'Microsoft.ContainerService/managedClusters/agentPools@2025-01-01' = [for pool in appPools: {
  parent: cluster
  name: pool.name
  properties: {
    count: pool.count
    vmSize: pool.vmSize
    osType: 'Linux'
    osSKU: 'Ubuntu'
    mode: 'User'
    type: 'VirtualMachineScaleSets'
    availabilityZones: pool.zones
    enableAutoScaling: false
    orchestratorVersion: kubernetesVersion
    nodeLabels: union(pool.?nodeLabels ?? {}, {
      workload: 'thesis-app'
      experimentPool: pool.name
    })
    nodeTaints: [
      'workload=thesis-app:NoSchedule'
    ]
  }
}]

output clusterName string = cluster.name
output clusterResourceId string = cluster.id
output applicationPoolNames array = [for pool in appPools: pool.name]
