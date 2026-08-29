using '../aks-region.bicep'

param location = 'westeurope'
param clusterName = 'thesis-aks-region-a'
param aksTier = 'Free'
param kubernetesVersion = '1.35.7'
param systemPoolVmSize = 'Standard_B2s'
param systemPoolCount = 1
param systemPoolZones = []
param appPools = [
  {
    name: 'app'
    count: 2
    vmSize: 'Standard_D2as_v5'
    zones: []
    nodeLabels: {
      regionRole: 'region-a'
      configuration: 'e2'
    }
  }
]
param tags = {
  project: 'masters-thesis'
  phase: 'azure-ha'
  configuration: 'E2'
  regionRole: 'region-a'
  owner: 'robyn'
}
