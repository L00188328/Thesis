targetScope = 'resourceGroup'

param profileName string
param endpointName string
param originGroupName string = 'thesis-origins'
param regionAOriginHost string
param regionBOriginHost string
param regionAPriority int
param regionBPriority int
param tags object = {}

resource profile 'Microsoft.Cdn/profiles@2024-02-01' = {
  name: profileName
  location: 'global'
  tags: tags
  sku: {
    name: 'Standard_AzureFrontDoor'
  }
}

resource endpoint 'Microsoft.Cdn/profiles/afdEndpoints@2024-02-01' = {
  parent: profile
  name: endpointName
  location: 'global'
  tags: tags
  properties: {
    enabledState: 'Enabled'
  }
}

resource originGroup 'Microsoft.Cdn/profiles/originGroups@2024-02-01' = {
  parent: profile
  name: originGroupName
  properties: {
    healthProbeSettings: {
      probeIntervalInSeconds: 10
      probePath: '/ready'
      probeProtocol: 'Http'
      probeRequestType: 'GET'
    }
    loadBalancingSettings: {
      additionalLatencyInMilliseconds: 1000
      sampleSize: 4
      successfulSamplesRequired: 3
    }
    sessionAffinityState: 'Disabled'
  }
}

resource regionAOrigin 'Microsoft.Cdn/profiles/originGroups/origins@2024-02-01' = {
  parent: originGroup
  name: 'region-a'
  properties: {
    enabledState: 'Enabled'
    hostName: regionAOriginHost
    httpPort: 80
    httpsPort: 443
    originHostHeader: regionAOriginHost
    priority: regionAPriority
    weight: 1000
    enforceCertificateNameCheck: false
  }
}

resource regionBOrigin 'Microsoft.Cdn/profiles/originGroups/origins@2024-02-01' = {
  parent: originGroup
  name: 'region-b'
  properties: {
    enabledState: 'Enabled'
    hostName: regionBOriginHost
    httpPort: 80
    httpsPort: 443
    originHostHeader: regionBOriginHost
    priority: regionBPriority
    weight: 1000
    enforceCertificateNameCheck: false
  }
}

resource route 'Microsoft.Cdn/profiles/afdEndpoints/routes@2024-02-01' = {
  parent: endpoint
  name: 'graphql-and-ui'
  properties: {
    originGroup: {
      id: originGroup.id
    }
    supportedProtocols: [
      'Http'
      'Https'
    ]
    patternsToMatch: [
      '/*'
    ]
    forwardingProtocol: 'HttpOnly'
    linkToDefaultDomain: 'Enabled'
    httpsRedirect: 'Enabled'
    enabledState: 'Enabled'
    cacheConfiguration: null
  }
  dependsOn: [
    regionAOrigin
    regionBOrigin
  ]
}

output frontDoorHostname string = endpoint.properties.hostName
