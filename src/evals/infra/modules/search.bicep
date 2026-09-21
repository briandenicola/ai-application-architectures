param location string
param tags object
param searchServiceName string

@description('Basic is sufficient for a 12-document demo corpus and keeps cost low.')
param sku string = 'basic'

resource search 'Microsoft.Search/searchServices@2025-05-01' = {
  name: searchServiceName
  location: location
  tags: tags
  sku: { name: sku }
  identity: { type: 'SystemAssigned' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'Default'
    publicNetworkAccess: 'enabled'
    // RBAC only. Admin/query keys are disabled outright, which is what makes the
    // "keyless" claim in the demo true rather than aspirational.
    disableLocalAuth: true
    semanticSearch: 'standard'
  }
}

output searchServiceName string = search.name
output searchServiceId string = search.id
output searchEndpoint string = 'https://${search.name}.search.windows.net'
output principalId string = search.identity.principalId
