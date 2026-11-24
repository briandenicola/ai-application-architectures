resource "azurerm_log_analytics_workspace" "this" {
  name                         = "${local.resource_name}-logs"
  resource_group_name          = azurerm_resource_group.this.name
  location                     = azurerm_resource_group.this.location
  sku                          = "PerGB2018"
  retention_in_days            = 30
  daily_quota_gb               = 1
  local_authentication_enabled = false
  tags                         = local.tags
}

resource "azurerm_application_insights" "this" {
  name                         = "${local.resource_name}-appi"
  resource_group_name          = azurerm_resource_group.this.name
  location                     = azurerm_resource_group.this.location
  application_type             = "web"
  workspace_id                 = azurerm_log_analytics_workspace.this.id
  retention_in_days            = 30
  daily_data_cap_in_gb         = 1
  sampling_percentage          = 100
  local_authentication_enabled = false
  tags                         = local.tags
}

resource "azurerm_role_assignment" "project_telemetry_publisher" {
  scope                = azurerm_application_insights.this.id
  role_definition_name = "Monitoring Metrics Publisher"
  principal_id         = azapi_resource.project.output.identity.principalId
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "operator_telemetry_reader" {
  for_each = {
    application = azurerm_application_insights.this.id
    workspace   = azurerm_log_analytics_workspace.this.id
  }

  scope                = each.value
  role_definition_name = "Log Analytics Reader"
  principal_id         = var.operator_object_id
}
