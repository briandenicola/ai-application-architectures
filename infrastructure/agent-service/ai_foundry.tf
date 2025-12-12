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
      customSubDomainName    = local.resource_name
      publicNetworkAccess    = "Enabled"
      restrictOutboundNetworkAccess = true
      networkAcls = {
        defaultAction = "Allow"
      }
      networkInjections = [
        {
          scenario                   = "agent"
          subnetArmId                = azurerm_subnet.agents.id
          useMicrosoftManagedNetwork = false
        }
      ]
      userOwnedStorageAccounts = [
        {
          id = azurerm_storage_account.this.id
        }
      ]
    }
  }

  response_export_values = [
    "properties.endpoint"
  ]
}

data "azurerm_cognitive_account" "ai_foundry" {
  depends_on          = [azapi_resource.ai_foundry]
  name                = local.ai_services_name
  resource_group_name = azurerm_resource_group.this.name
}


data "azurerm_monitor_diagnostic_categories" "ai" {
  resource_id = azapi_resource.ai_foundry.id
}

resource "azurerm_monitor_diagnostic_setting" "ai" {
  depends_on = [
    data.azurerm_monitor_diagnostic_categories.ai
  ]
  name                       = "diag"
  target_resource_id         = azapi_resource.ai_foundry.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.ai.log_category_types)
    content {
      category = enabled_log.value
    }
  }

  enabled_metric {
    category = "AllMetrics"
  }
}