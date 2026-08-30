using '../front-door.bicep'

param profileName = 'thesis-ha-frontdoor'
param endpointName = 'thesis-ha'
param originGroupName = 'thesis-origins'
param regionAOriginHost = readEnvironmentVariable('REGION_A_ORIGIN_HOST')
param regionBOriginHost = readEnvironmentVariable('REGION_B_ORIGIN_HOST')
param regionAPriority = 1
param regionBPriority = 1
param tags = {
  project: 'masters-thesis'
  phase: 'azure-ha'
  configuration: 'G2'
  run: 'g2-series'
  owner: 'robyn'
}
