using '../aks-region.bicep'

param location = 'norwayeast'
param clusterName = 'thesis-aks-region-b'
param aksTier = 'Free'
param kubernetesVersion = '1.35.7'
param systemPoolVmSize = 'Standard_B2s'
param systemPoolCount = 1
param systemPoolZones = [
  '1'
]
param appPools = [
  {
    name: 'appzone1'
    count: 1
    vmSize: 'Standard_D2as_v4'
    zones: [
      '1'
    ]
    nodeLabels: {
      regionRole: 'region-b'
    }
  }
  {
    name: 'appzone2'
    count: 1
    vmSize: 'Standard_D2as_v4'
    zones: [
      '2'
    ]
    nodeLabels: {
      regionRole: 'region-b'
    }
  }
]
param tags = {
  project: 'masters-thesis'
  phase: 'azure-ha'
  configuration: 'G1-G2'
  run: 'multi-region-series'
  regionRole: 'region-b'
  owner: 'robyn'
}
