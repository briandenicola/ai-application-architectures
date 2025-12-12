resource "random_string" "unique" {
  length      = 5
  min_numeric = 5
  numeric     = true
  special     = false
  lower       = true
  upper       = false
}

resource "azapi_resource" "ai_foundry" {
  type                      = "Microsoft.CognitiveServices/accounts@2025-10-01-preview"
  name                      = local.ai_services_name
  parent_id                 = azurerm_resource_group.this.id
  location                  = azurerm_resource_group.this.location
  schema_validation_enabled = false

  body = {
    kind = "AIServices",
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }

    properties = {
      disableLocalAuth       = false
      allowProjectManagement = true
      customSubDomainName    = "agentsvc${random_string.unique.result}"
      publicNetworkAccess    = "Enabled"
    }
  }

  response_export_values = [
    "properties.endpoint"
  ]
}