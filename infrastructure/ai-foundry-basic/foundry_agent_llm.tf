resource "azapi_resource" "global" {
  type      = "Microsoft.CognitiveServices/accounts@2024-10-01"
  name      = "${local.openai_name}-global"
  location  = azurerm_resource_group.this.location
  parent_id = azurerm_resource_group.this.id

  body = {
    sku = {
      name = "S0"
    },
    kind = "AIServices",
    properties = {
      customSubDomainName = "${local.openai_name}-global"
      publicNetworkAccess = "Enabled"
    }
  }
}

data "azurerm_cognitive_account" "global" {
  depends_on          = [azapi_resource.global]
  name                = "${local.openai_name}-global"
  resource_group_name = azurerm_resource_group.this.name
}

resource "azurerm_monitor_diagnostic_setting" "global" {
  depends_on = [
    data.azurerm_monitor_diagnostic_categories.this
  ]
  name                       = "diag"
  target_resource_id         = data.azurerm_cognitive_account.global.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.this.log_category_types)
    content {
      category = enabled_log.value
    }
  }

  metric {
    category = "AllMetrics"
  }
}
