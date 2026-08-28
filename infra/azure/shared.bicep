targetScope = 'resourceGroup'

@description('Azure region for shared supporting dependencies.')
param location string

@description('Globally unique lowercase resource prefix.')
@minLength(3)
@maxLength(20)
param namePrefix string

@secure()
@description('PostgreSQL administrator password supplied only at deployment time.')
param postgresAdminPassword string

param postgresAdminLogin string = 'thesisadmin'
param postgresSkuName string = 'Standard_B1ms'
param postgresTier string = 'Burstable'
param postgresStorageSizeGB int = 32
param eventHubsSkuName string = 'Standard'
param eventHubsCapacity int = 1
param eventHubsRetentionDays int = 1
param tags object = {}

var acrName = '${namePrefix}acr'
var eventHubsNamespaceName = '${namePrefix}-events'
var postgresServerName = '${namePrefix}-postgres'

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource eventNamespace 'Microsoft.EventHub/namespaces@2024-01-01' = {
  name: eventHubsNamespaceName
  location: location
  tags: tags
  sku: {
    name: eventHubsSkuName
    tier: eventHubsSkuName
    capacity: eventHubsCapacity
  }
  properties: {
    isAutoInflateEnabled: false
    publicNetworkAccess: 'Enabled'
    minimumTlsVersion: '1.2'
  }
}

resource logisticEvents 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  parent: eventNamespace
  name: 'logistic-center-events'
  properties: {
    messageRetentionInDays: eventHubsRetentionDays
    partitionCount: 2
    status: 'Active'
  }
}

resource deliveryEvents 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  parent: eventNamespace
  name: 'delivery-base-events'
  properties: {
    messageRetentionInDays: eventHubsRetentionDays
    partitionCount: 2
    status: 'Active'
  }
}

resource kafkaAuthorization 'Microsoft.EventHub/namespaces/authorizationRules@2024-01-01' = {
  parent: eventNamespace
  name: 'aggregator-kafka'
  properties: {
    rights: [
      'Listen'
      'Send'
    ]
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresServerName
  location: location
  tags: tags
  sku: {
    name: postgresSkuName
    tier: postgresTier
  }
  properties: {
    version: '16'
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    availabilityZone: '1'
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
    storage: {
      storageSizeGB: postgresStorageSizeGB
      autoGrow: 'Enabled'
    }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: 'shipments'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource allowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

output acrLoginServer string = registry.properties.loginServer
output eventHubsBootstrapServers string = '${eventNamespace.name}.servicebus.windows.net:9093'
output eventHubsNamespaceName string = eventNamespace.name
output postgresHost string = '${postgres.name}.postgres.database.azure.com'
output postgresDatabase string = database.name
