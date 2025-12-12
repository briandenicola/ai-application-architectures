resource "azapi_resource" "ai_foundry_project" {
  type                      = "Microsoft.CognitiveServices/accounts/projects@2025-10-01-preview"
  name                      = var.foundry_project.name
  parent_id                 = var.foundry_project.ai_foundry.id
  location                  = var.foundry_project.location
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