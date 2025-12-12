resource "azapi_resource" "application_insights_connection" {
  depends_on = [
    azapi_resource.ai_foundry_project,
    azurerm_application_insights.this
  ]
  type                      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01"
  name                      = azurerm_application_insights.this.name
  parent_id                 = azapi_resource.ai_foundry_project.id
  schema_validation_enabled = false

  body = {
    name = azurerm_application_insights.this.name
    properties = {
      category      = "AppInsights"
      authType      = "ApiKey"
      isSharedToAll = false 
      metadata = {
        ApiType    = "Azure"
        ResourceId = azurerm_application_insights.this.id
        location   = azurerm_resource_group.this.location
      }
      target   = azurerm_application_insights.this.id
      credentials = {
        key = azurerm_application_insights.this.connection_string 
      }      
    }
  }
}

resource "azapi_resource" "cosmosdb_connection" {
  depends_on = [
    azurerm_cosmosdb_account.this
  ]
  type                      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01"
  name                      = azurerm_cosmosdb_account.this.name
  parent_id                 = azapi_resource.ai_foundry_project.id
  schema_validation_enabled = false

  body = {
    name = azurerm_cosmosdb_account.this.name
    properties = {
      category = "CosmosDb"
      target   = azurerm_cosmosdb_account.this.endpoint
      authType = "AAD"
      metadata = {
        ApiType    = "Azure"
        ResourceId = azurerm_cosmosdb_account.this.id
        location   = azurerm_resource_group.this.location
      }
    }
  }

  response_export_values = [
    "identity.principalId"
  ]
}

resource "azapi_resource" "storage_connection" {
  depends_on = [
    azurerm_storage_account.this
  ]
  type                      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01"
  name                      = azurerm_storage_account.this.name
  parent_id                 = azapi_resource.ai_foundry_project.id
  schema_validation_enabled = false

  body = {
    name = azurerm_storage_account.this.name
    properties = {
      category = "AzureStorageAccount"
      target   = azurerm_storage_account.this.primary_blob_endpoint
      authType = "AAD"
      metadata = {
        ApiType    = "Azure"
        ResourceId = azurerm_storage_account.this.id
        location   = azurerm_resource_group.this.location
      }
    }
  }

  response_export_values = [
    "identity.principalId"
  ]

}

resource "azapi_resource" "aisearch_connection" {
  depends_on = [
    azapi_resource.ai_search,
  ]
  type                      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01"
  name                      = azapi_resource.ai_search.name
  parent_id                 = azapi_resource.ai_foundry_project.id
  schema_validation_enabled = false

  body = {
    name = azapi_resource.ai_search.name
    properties = {
      category = "CognitiveSearch"
      target   = "https://${azapi_resource.ai_search.name}.search.windows.net"
      authType = "AAD"
      metadata = {
        ApiType    = "Azure"
        ApiVersion = "2025-05-01-preview"
        ResourceId = azapi_resource.ai_search.id
        location   = azurerm_resource_group.this.location
      }
    }
  }

  response_export_values = [
    "identity.principalId"
  ]
}
