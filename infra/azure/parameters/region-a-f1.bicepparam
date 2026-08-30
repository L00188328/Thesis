using '../aks-region.bicep'

param location = 'italynorth'
param clusterName = 'thesis-aks-region-a'
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
      regionRole: 'region-a'
      configuration: 'f1'
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
      regionRole: 'region-a'
      configuration: 'f1'
    }
  }
]
param tags = {
  project: 'masters-thesis'
  phase: 'azure-ha'
  configuration: 'F1'
  run: 'f1-series'
  regionRole: 'region-a'
  owner: 'robyn'
}
