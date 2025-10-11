resource "azapi_resource" "ai_foundry_project" {
  type                      = "Microsoft.CognitiveServices/accounts/projects@2025-06-01"
  name                      = var.foundry_project.name
  parent_id                 = var.foundry_project.ai_foundry_id
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
      displayName = var.foundry_project.name
      description = var.foundry_project.tag
    }
  }

  response_export_values = [
    "identity.principalId",
    "properties.internalId"
  ]
}