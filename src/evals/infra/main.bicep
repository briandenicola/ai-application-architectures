targetScope = 'resourceGroup'

// ─────────────────────────────────────────────────────────────────────────────
// Meridian Foundry Evals — demo infrastructure
// Governed by specs/001-foundry-evals-demo/contracts.md §1
// Non-negotiable: keyless. No key, SAS, or secret is ever emitted as an output.
// ─────────────────────────────────────────────────────────────────────────────

@minLength(1)
@maxLength(24)
@description('Name of the azd environment. Used to derive unique resource names.')
param environmentName string

@description('Azure region. Must support the pinned model versions — see T0.1.')
param location string

@description('Object ID of the deploying user or service principal. Receives data-plane roles.')
param principalId string

@allowed(['User', 'ServicePrincipal'])
@description('Type of the deploying principal. Affects how role assignments are evaluated.')
param principalType string = 'User'

@description('Search index holding the Meridian synthetic corpus.')
param searchIndexName string = 'meridian-docs'

@description('Index holding the AI Platform FinOps corpus (corpus-finops/).')
param finopsSearchIndexName string = 'meridian-aiops-costs'

@description('Search index for the people-analytics corpus. Third track; see docs/hr-traps.md.')
param hrSearchIndexName string = 'meridian-people-analytics'

// ── Model deployments ────────────────────────────────────────────────────────
// Versions are pinned. "latest" would break the reproducibility non-negotiable.
// Verified available in centralus on 2026-09-21 (T0.1):
//   az cognitiveservices model list --location centralus

param agentModelName string = 'gpt-5.5'
param agentModelVersion string = '2026-04-24'
// 50 was not a considered number, it was the template default, and it cost two
// failed 26-case FinOps runs before anyone looked at it (#17). Foundry runs the
// dataset concurrently and the FinOps answers are long tables, so the agent
// exhausts 50K TPM partway through. The rate limit does not surface as a quota
// error either -- the evaluator receives a null response and the harness exits
// 2 with "Response is a required input and cannot be None".
//
// Subscription quota for GlobalStandard gpt-5.5 in centralus is 1000. We were
// throttling at 5% of our own allowance. 500 leaves headroom for a second
// concurrent run without going near the ceiling.
param agentModelCapacity int = 500

// The judge is deliberately NOT a reasoning model: Foundry's built-in evaluators
// send max_tokens, which reasoning models reject outright. A non-reasoning judge
// also accepts temperature and seed, so scoring is reproducible. See ADR-0006.
param judgeModelName string = 'gpt-4.1-mini'
param judgeModelVersion string = '2025-04-14'
// Four evaluators fire per case, so the judge burns tokens faster than the
// agent does. Raised alongside the agent for the same reason.
param judgeModelCapacity int = 500

param embeddingModelName string = 'text-embedding-3-large'
param embeddingModelVersion string = '1'
param embeddingModelCapacity int = 50

param foundryProjectName string = 'meridian-evals'

var token = toLower(uniqueString(subscription().id, resourceGroup().id, environmentName))
var prefix = 'mwp${take(token, 8)}'

var tags = {
  'azd-env-name': environmentName
  solution: 'meridian-foundry-evals'
  dataClassification: 'synthetic-demo-only'
}

// ── Observability ────────────────────────────────────────────────────────────

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    tags: tags
    logAnalyticsName: '${prefix}-law'
    applicationInsightsName: '${prefix}-appi'
  }
}

// ── Azure AI Search (powers the Foundry IQ knowledge base) ───────────────────

module search 'modules/search.bicep' = {
  name: 'search'
  params: {
    location: location
    tags: tags
    searchServiceName: '${prefix}-search'
  }
}

// ── Foundry account, project, and model deployments ──────────────────────────

module foundry 'modules/foundry.bicep' = {
  name: 'foundry'
  params: {
    location: location
    tags: tags
    accountName: '${prefix}-foundry'
    projectName: foundryProjectName
    agentModelName: agentModelName
    agentModelVersion: agentModelVersion
    agentModelCapacity: agentModelCapacity
    judgeModelName: judgeModelName
    judgeModelVersion: judgeModelVersion
    judgeModelCapacity: judgeModelCapacity
    embeddingModelName: embeddingModelName
    embeddingModelVersion: embeddingModelVersion
    embeddingModelCapacity: embeddingModelCapacity
    applicationInsightsId: monitoring.outputs.applicationInsightsId
    applicationInsightsConnectionString: monitoring.outputs.connectionString
    searchServiceId: search.outputs.searchServiceId
    searchServiceEndpoint: search.outputs.searchEndpoint
  }
}

// ── RBAC: least privilege, resource-scoped ───────────────────────────────────

module rbac 'modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    searchServiceName: search.outputs.searchServiceName
    foundryAccountPrincipalId: foundry.outputs.accountPrincipalId
    foundryAccountName: foundry.outputs.accountName
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    searchPrincipalId: search.outputs.principalId
    foundryProjectPrincipalId: foundry.outputs.projectPrincipalId
    deployerPrincipalId: principalId
    deployerPrincipalType: principalType
  }
}

// ── Outputs: the contract. Consumed by azd as environment variables. ─────────

output AZURE_AI_FOUNDRY_NAME string = foundry.outputs.accountName
output AZURE_AI_PROJECT_NAME string = foundry.outputs.projectName
output AZURE_AI_PROJECT_ENDPOINT string = foundry.outputs.projectEndpoint
output AZURE_AI_AGENT_MODEL_DEPLOYMENT string = agentModelName
output AZURE_AI_JUDGE_MODEL_DEPLOYMENT string = judgeModelName
output AZURE_AI_EMBEDDING_DEPLOYMENT string = embeddingModelName

output AZURE_SEARCH_NAME string = search.outputs.searchServiceName
output AZURE_SEARCH_ENDPOINT string = search.outputs.searchEndpoint

output AZURE_AI_FOUNDRY_ENDPOINT string = foundry.outputs.accountEndpoint
output AZURE_SEARCH_INDEX string = searchIndexName
output AZURE_SEARCH_FINOPS_INDEX string = finopsSearchIndexName
output AZURE_SEARCH_HR_INDEX string = hrSearchIndexName
output AZURE_SEARCH_SERVICE_ID string = search.outputs.searchServiceId
output AZURE_SEARCH_CONNECTION_ID string = foundry.outputs.searchConnectionId
output AZURE_SEARCH_CONNECTION_NAME string = foundry.outputs.searchConnectionName

output AZURE_APPLICATION_INSIGHTS_CONNECTION_STRING string = monitoring.outputs.connectionString
output AZURE_RESOURCE_GROUP string = resourceGroup().name
output AZURE_LOCATION string = location

output RBAC_APPLIED bool = rbac.outputs.applied
