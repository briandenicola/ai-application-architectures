resource "azapi_resource" "bing_grounding" {
  schema_validation_enabled = false
  type                      = "Microsoft.Bing/accounts@2025-05-01-preview"
  name                      = local.bing_name
  parent_id                 = azurerm_resource_group.this.id
  location                  = "Global"
  
  body = {
    kind = "Bing.Grounding"
    sku = {
      name = "G1"
    }
    properties = {
    }
  }
}

resource "azurerm_monitor_diagnostic_setting" "bing" {
  name                       = "diag"
  target_resource_id         = azapi_resource.bing_grounding.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  metric {
    category = "AllMetrics"
  }
}