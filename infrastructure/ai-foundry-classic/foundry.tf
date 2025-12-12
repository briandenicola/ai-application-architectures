data "azurerm_monitor_diagnostic_categories" "this" {
  resource_id = azurerm_cognitive_account.this.id
}

resource "azurerm_cognitive_account" "this" {
  name                  = local.foundry_name
  location              = azurerm_resource_group.this.location
  resource_group_name   = azurerm_resource_group.this.name
  kind                  = "AIServices"
  custom_subdomain_name = local.foundry_name
  sku_name              = "S0"
}

resource "azurerm_monitor_diagnostic_setting" "this" {
  depends_on = [
    data.azurerm_monitor_diagnostic_categories.this
  ]

  name                       = "diag"
  target_resource_id         = azurerm_cognitive_account.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.this.log_category_types)
    content {
      category = enabled_log.value
    }

  }

  enabled_metric {
    category = "AllMetrics"
  }
}
