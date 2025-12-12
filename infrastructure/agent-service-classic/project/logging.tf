resource "azurerm_application_insights" "this" {
  name                          = local.app_insights_name  
  location                      = azurerm_resource_group.this.location
  resource_group_name           = azurerm_resource_group.this.name
  workspace_id                  = var.foundry_project.logs.workspace_id
  application_type              = "web"
}