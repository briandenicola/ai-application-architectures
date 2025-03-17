data "azurerm_monitor_diagnostic_categories" "this" {
  resource_id = azurerm_cognitive_account.this.id
}

resource "azurerm_cognitive_account" "this" {
  name                  = local.openai_name
  resource_group_name   = azurerm_resource_group.this.name
  location              = azurerm_resource_group.this.location
  custom_subdomain_name = local.openai_name
  kind                  = "OpenAI"

  sku_name = "S0"
}

resource "azurerm_cognitive_account" "embedding" {
  name                  = "${local.openai_name}-embedding"
  resource_group_name   = azurerm_resource_group.this.name
  location              = local.embedding_location
  custom_subdomain_name = "${local.openai_name}-embedding"
  kind                  = "OpenAI"

  sku_name = "S0"
}

resource "azapi_resource" "global" {
  type      = "Microsoft.CognitiveServices/accounts@2024-10-01"
  name      = "${local.openai_name}-global"
  location  = local.global_location
  parent_id = azurerm_resource_group.this.id

  body = {
    sku = {
        name =  "S0"
    },
    kind = "AIServices",
    properties = {
      customSubDomainName = "${local.openai_name}-global",
      publicNetworkAccess = "Enabled",
      
    }
  }
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

  metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "embedding" {
  depends_on = [
    data.azurerm_monitor_diagnostic_categories.this
  ]
  name                       = "diag"
  target_resource_id         = azurerm_cognitive_account.embedding.id
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
