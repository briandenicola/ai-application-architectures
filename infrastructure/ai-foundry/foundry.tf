data "azurerm_monitor_diagnostic_categories" "this" {
  resource_id = azurerm_cognitive_account.this.id
}

resource "azurerm_cognitive_account" "this" {
  name                  = local.foundry_name
  resource_group_name   = var.resource_group.name
  location              = var.resource_group.location
  kind                  = "OpenAI"
  custom_subdomain_name = local.foundry_name
  sku_name              = "S0"
}

resource "azurerm_monitor_diagnostic_setting" "this" {
  count = var.log_analytics.deploy ? 1 : 0

  depends_on = [
    data.azurerm_monitor_diagnostic_categories.this
  ]

  name                       = "diag"
  target_resource_id         = azurerm_cognitive_account.this.id
  log_analytics_workspace_id = var.log_analytics.workspace_id

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
