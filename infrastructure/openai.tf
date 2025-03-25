data "azurerm_monitor_diagnostic_categories" "this" {
  resource_id = azurerm_cognitive_account.regional.id
}

resource "azurerm_cognitive_account" "regional" {
  name                  = local.openai_name
  resource_group_name   = azurerm_resource_group.this.name
  location              = local.regional_location
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
  location  = azurerm_resource_group.this.location
  parent_id = azurerm_resource_group.this.id

  body = {
    sku = {
      name = "S0"
    },
    kind = "AIServices",
    properties = {
      customSubDomainName = "${local.openai_name}-global",
      publicNetworkAccess = "Enabled",

    }
  }
}
data "azurerm_cognitive_account" "global" {
  depends_on          = [azapi_resource.global]
  name                = "${local.openai_name}-global"
  resource_group_name = azurerm_resource_group.this.name
}

resource "azurerm_monitor_diagnostic_setting" "regional" {
  depends_on = [
    data.azurerm_monitor_diagnostic_categories.this
  ]
  name                       = "diag"
  target_resource_id         = azurerm_cognitive_account.regional.id
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
