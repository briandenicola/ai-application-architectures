resource "azurerm_ai_foundry_project" "this" {
  name               = local.project_name
  location           = azurerm_ai_foundry.this.location
  ai_services_hub_id = azurerm_ai_foundry.this.id

  identity {
    type = "SystemAssigned"
  }
}

data "azurerm_monitor_diagnostic_categories" "ai_project" {
  resource_id = azurerm_ai_foundry_project.this.id
}

resource "azurerm_monitor_diagnostic_setting" "ai_project" {
  depends_on = [
    data.azurerm_monitor_diagnostic_categories.ai_project
  ]
  name                       = "diag"
  target_resource_id         = azurerm_ai_foundry_project.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.ai_project.log_category_types)
    content {
      category = enabled_log.value
    }
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
