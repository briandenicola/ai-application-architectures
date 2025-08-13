resource "azapi_resource" "ai_foundry_project" {
  depends_on = [
    azapi_resource.ai_foundry,
    azurerm_private_endpoint.pe_storage,
    azurerm_private_endpoint.pe_cosmosdb,
    azurerm_private_endpoint.pe_aisearch,
    azurerm_private_endpoint.pe_aifoundry
  ]

  type                      = "Microsoft.CognitiveServices/accounts/projects@2025-06-01"
  name                      = local.project_name
  parent_id                 = azurerm_resource_group.this.id
  location                  = azurerm_resource_group.this.location
  schema_validation_enabled = false

  body = {
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }

    properties = {
      displayName = "Demo Project"
      description = "A project for the AI Foundry account with network secured deployed Agent"
    }
  }

  response_export_values = [
    "identity.principalId",
    "properties.internalId"
  ]
}