resource "azurerm_application_insights" "this" {
  name                          = local.app_insights_name  
  location                      = var.foundry_project.location
  resource_group_name           = var.foundry_project.resource_group.name
  workspace_id                  = var.foundry_project.logs.workspace_id
  application_type              = "web"
}