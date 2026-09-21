param location string
param tags object
param accountName string
param projectName string
param applicationInsightsId string
param searchServiceId string
param searchServiceEndpoint string

@description('Required in the connection metadata by the service, even though auth is keyless.')
@secure()
param applicationInsightsConnectionString string

param agentModelName string
param agentModelVersion string
param agentModelCapacity int

param judgeModelName string
param judgeModelVersion string
param judgeModelCapacity int

param embeddingModelName string
param embeddingModelVersion string
param embeddingModelCapacity int

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled'
    // Keyless non-negotiable. Entra tokens only.
    disableLocalAuth: true
    allowProjectManagement: true
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: 'Meridian Evals'
    description: 'Wealth management advisor agent — Foundry Evaluations demo. Synthetic data only.'
  }
}

// ── Model deployments ────────────────────────────────────────────────────────
// Everything below writes to the same Cognitive Services account, and the
// service rejects concurrent writes with RequestConflict. ARM parallelises by
// default, so the whole chain must be serialised explicitly:
//   account → project → agent → judge → embedding
// Removing any dependsOn here produces an intermittent `azd up` failure that
// looks like a naming conflict rather than a concurrency one.

resource agentModel 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: agentModelName
  dependsOn: [project]
  sku: {
    name: 'GlobalStandard'
    capacity: agentModelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: agentModelName
      version: agentModelVersion
    }
    versionUpgradeOption: 'NoAutoUpgrade'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

resource judgeModel 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: judgeModelName
  dependsOn: [agentModel]
  sku: {
    name: 'GlobalStandard'
    capacity: judgeModelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: judgeModelName
      version: judgeModelVersion
    }
    versionUpgradeOption: 'NoAutoUpgrade'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

resource embeddingModel 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: embeddingModelName
  dependsOn: [judgeModel]
  sku: {
    // GlobalStandard, not Standard — Standard is not offered for
    // text-embedding-3-large in centralus. Verified 2026-09-21.
    name: 'GlobalStandard'
    capacity: embeddingModelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: embeddingModelName
      version: embeddingModelVersion
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}

// Trace evaluation runs into Application Insights so the portal can show them.
resource appInsightsConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = {
  parent: project
  name: 'appinsights'
  // Same account, same serialisation requirement as the model deployments.
  dependsOn: [embeddingModel]
  properties: {
    category: 'AppInsights'
    target: applicationInsightsId
    // Only ProjectManagedIdentity and ApiKey are accepted here — 'AAD' is
    // rejected at validation. ProjectManagedIdentity is the keyless option and
    // is why the project carries a SystemAssigned identity.
    //
    // BCP036 is suppressed because the Bicep type definition for this property
    // is out of date: it advertises 'AAD' and omits 'ProjectManagedIdentity'.
    // The service rejects the former and requires the latter. Verified against
    // the live API 2026-09-21. Re-check when the type definitions catch up.
    #disable-next-line BCP036
    authType: 'ProjectManagedIdentity'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: applicationInsightsId
      // The service requires this even under ProjectManagedIdentity auth.
      // It is metadata on the connection, not a Bicep output — the
      // no-secrets-in-outputs contract is unaffected.
      ApplicationInsightsConnectionString: applicationInsightsConnectionString
    }
  }
}

// Prompt agents ground through the `azure_ai_search` tool, which resolves the
// index through a PROJECT CONNECTION rather than a raw endpoint. Without this
// connection the agents can still be created — the agent API does not validate
// tools at creation time — but every grounded question fails at run time.
// See docs/adr/0005-agent-grounding-via-search-connection.md.
resource searchConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = {
  parent: project
  name: 'search'
  // Serialised behind the App Insights connection for the same reason the model
  // deployments are serialised: concurrent writes to one account are rejected.
  dependsOn: [appInsightsConnection]
  properties: {
    category: 'CognitiveSearch'
    target: searchServiceEndpoint
    // Keyless. The search service has disableLocalAuth: true, so ApiKey is not
    // an option even if we wanted it.
    #disable-next-line BCP036
    authType: 'ProjectManagedIdentity'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: searchServiceId
      Location: location
    }
  }
}

output accountName string = account.name
output accountEndpoint string = 'https://${account.name}.cognitiveservices.azure.com'
output accountId string = account.id
output accountPrincipalId string = account.identity.principalId
output projectName string = project.name
output projectId string = project.id
output projectPrincipalId string = project.identity.principalId
output projectEndpoint string = 'https://${account.name}.services.ai.azure.com/api/projects/${project.name}'
output appInsightsConnectionName string = appInsightsConnection.name
output searchConnectionName string = searchConnection.name
output searchConnectionId string = searchConnection.id
output deployedModels array = [agentModel.name, judgeModel.name, embeddingModel.name]
