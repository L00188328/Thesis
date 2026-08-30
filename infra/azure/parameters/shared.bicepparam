using '../shared.bicep'

param location = 'westeurope'
param namePrefix = 'thesisha'
param postgresAdminLogin = 'thesisadmin'
param postgresAdminPassword = readEnvironmentVariable('AZURE_POSTGRES_ADMIN_PASSWORD')
param postgresSkuName = 'Standard_B1ms'
param postgresTier = 'Burstable'
param postgresStorageSizeGB = 32
param eventHubsSkuName = 'Standard'
param eventHubsCapacity = 1
param eventHubsRetentionDays = 1
param tags = {
  project: 'masters-thesis'
  phase: 'azure-ha'
  configuration: 'shared'
  run: 'shared-series'
  owner: 'robyn'
}
