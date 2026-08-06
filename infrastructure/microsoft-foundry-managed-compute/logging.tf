resource "azurerm_log_analytics_workspace" "this" {
  name                          = local.loganalytics_name
  location                      = azurerm_resource_group.this.location
  resource_group_name           = azurerm_resource_group.this.name
  sku                           = "PerGB2018"
  daily_quota_gb                = 1
}
