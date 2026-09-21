param location string
param tags object
param logAnalyticsName string
param applicationInsightsName string

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    // Demo-only workspace. Eval output contains model responses — short retention,
    // and it is destroyed on teardown.
    retentionInDays: 30
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    DisableLocalAuth: true
  }
}

output logAnalyticsId string = logAnalytics.id
output applicationInsightsId string = applicationInsights.id
output connectionString string = applicationInsights.properties.ConnectionString
output applicationInsightsName string = applicationInsights.name
