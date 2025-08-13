resource "azurerm_ai_foundry" "this" {
  depends_on            = [azurerm_role_assignment.key_user, azurerm_role_assignment.storage_owner]
  name                  = local.hub_name
  location              = local.location
  resource_group_name   = azurerm_resource_group.this.name
  storage_account_id    = azurerm_storage_account.this.id
  key_vault_id          = azurerm_key_vault.this.id
  container_registry_id = azurerm_container_registry.this.id
  application_insights_id = azurerm_application_insights.this.id

  identity {
    type = "SystemAssigned"
  }
}

data "azurerm_monitor_diagnostic_categories" "ai" {
  resource_id = azurerm_ai_foundry.this.id
}

resource "azurerm_monitor_diagnostic_setting" "ai" {
  depends_on = [
    data.azurerm_monitor_diagnostic_categories.ai
  ]
  name                       = "diag"
  target_resource_id         = azurerm_ai_foundry.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.ai.log_category_types)
    content {
      category = enabled_log.value
    }
  }

  metric {
    category = "AllMetrics"
  }
}
