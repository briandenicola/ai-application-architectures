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
        location   = var.foundry_project.location
      }
      target   = azurerm_application_insights.this.id
      credentials = {
        key = azurerm_application_insights.this.connection_string 
      }      
    }
  }
}
