// ─────────────────────────────────────────────────────────────────────────────
// Least-privilege, resource-scoped role assignments.
// Governed by specs/001-foundry-evals-demo/contracts.md §1.
// No subscription-scope grants. No Owner. No Contributor on data planes.
// ─────────────────────────────────────────────────────────────────────────────

param searchServiceName string
param foundryAccountName string
param applicationInsightsName string

@description('Search service system-assigned MI. Calls the embedding model for query vectorisation.')
param searchPrincipalId string

@description('Foundry project system-assigned MI. Queries the index, resolves citations.')
param foundryProjectPrincipalId string
param foundryAccountPrincipalId string

@description('The human or SP running azd up. Needs data-plane write to set the demo up.')
param deployerPrincipalId string
param deployerPrincipalType string

// Built-in role definition IDs.
var roles = {
  searchIndexDataReader: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
  searchIndexDataContributor: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
  searchServiceContributor: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
  cognitiveServicesUser: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  azureAIUser: '53ca6127-db72-4b80-b1b0-d745d6d5456d'
  monitoringMetricsPublisher: '3913510d-42f4-4e42-8a64-420c390055eb'
}

resource searchService 'Microsoft.Search/searchServices@2025-05-01' existing = {
  name: searchServiceName
}

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

// ── The azure_ai_search tool authenticates as the FOUNDRY ACCOUNT identity ──
//
// Not the project identity, which is the intuitive guess and is wrong. Microsoft
// documents both of these roles on the account identity:
// https://learn.microsoft.com/azure/foundry/agents/how-to/tools/ai-search
//
// When these are missing the agent still CREATES successfully and every
// grounded question fails at run time with a generic "Access denied" that names
// no identity. Verified the hard way on 2026-09-21 — see ADR-0005.
//
// Propagation to the Search data plane took roughly 5 minutes in testing, which
// is why postprovision.sh waits before smoke-testing.
resource accountQueriesIndex 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: searchService
  name: guid(searchService.id, foundryAccountPrincipalId, roles.searchIndexDataContributor)
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roles.searchIndexDataContributor
    )
    principalId: foundryAccountPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource accountResolvesIndex 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: searchService
  name: guid(searchService.id, foundryAccountPrincipalId, roles.searchServiceContributor)
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roles.searchServiceContributor
    )
    principalId: foundryAccountPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ── Foundry project performs agentic retrieval and resolves citations ────────

resource projectQueriesIndex 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: searchService
  name: guid(searchService.id, foundryProjectPrincipalId, roles.searchIndexDataReader)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchIndexDataReader)
    principalId: foundryProjectPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// The App Insights connection uses ProjectManagedIdentity auth, and the
// component has DisableLocalAuth: true — so without this grant the connection
// resolves but every trace write is silently rejected.
resource projectWritesTelemetry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: applicationInsights
  name: guid(applicationInsights.id, foundryProjectPrincipalId, roles.monitoringMetricsPublisher)
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roles.monitoringMetricsPublisher
    )
    principalId: foundryProjectPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ── Deployer: uploads the corpus, builds the knowledge base, runs evals ──────
resource deployerManagesSearch 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: searchService
  name: guid(searchService.id, deployerPrincipalId, roles.searchServiceContributor)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchServiceContributor)
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
  }
}

resource deployerWritesIndex 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: searchService
  name: guid(searchService.id, deployerPrincipalId, roles.searchIndexDataContributor)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchIndexDataContributor)
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
  }
}

resource deployerUsesFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundryAccount
  name: guid(foundryAccount.id, deployerPrincipalId, roles.azureAIUser)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.azureAIUser)
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
  }
}

resource deployerCallsModels 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundryAccount
  name: guid(foundryAccount.id, deployerPrincipalId, roles.cognitiveServicesUser)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.cognitiveServicesUser)
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
  }
}

// ── Search calls the embedding + chat models for integrated vectorization ────

resource searchCallsModels 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundryAccount
  name: guid(foundryAccount.id, searchPrincipalId, roles.cognitiveServicesUser)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.cognitiveServicesUser)
    principalId: searchPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output applied bool = true
output assignmentCount int = 9
output assignments array = [
  projectQueriesIndex.name
  projectWritesTelemetry.name
  deployerManagesSearch.name
  deployerWritesIndex.name
  deployerUsesFoundry.name
  deployerCallsModels.name
  searchCallsModels.name
]
