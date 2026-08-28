targetScope = 'resourceGroup'

@description('Existing Azure Container Registry name in this resource group.')
param registryName string

@description('AKS kubelet managed-identity object ID returned by az aks show.')
param kubeletObjectId string

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: registryName
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, kubeletObjectId, 'AcrPull')
  scope: registry
  properties: {
    principalId: kubeletObjectId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
  }
}
