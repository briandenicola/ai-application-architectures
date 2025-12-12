resource "azapi_resource" "ai_foundry_project_capability_host" {
  depends_on = [
    azapi_resource.aisearch_connection,
    azapi_resource.cosmosdb_connection,
    azapi_resource.storage_connection,
    time_sleep.wait_rbac
  ]
  type                      = "Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview"
  name                      = local.capability_host_name
  parent_id                 = azapi_resource.ai_foundry_project.id
  schema_validation_enabled = false

  body = {
    properties = {
      capabilityHostKind = "Agents"
      vectorStoreConnections = [
        azapi_resource.ai_search.name
      ]
      storageConnections = [
        azurerm_storage_account.this.name
      ]
      threadStorageConnections = [
        azurerm_cosmosdb_account.this.name
      ]
    }
  }
}
