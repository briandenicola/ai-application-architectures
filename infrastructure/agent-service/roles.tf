resource "azurerm_role_assignment" "ai_foundry_developer" {
  depends_on = [
    azurerm_resource_group.this
  ]
  scope                = azurerm_resource_group.this.id
  role_definition_name = "Azure AI Developer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "ai_foundry_project_manager" {
  depends_on = [
    azurerm_resource_group.this
  ]
  scope                = azurerm_resource_group.this.id
  role_definition_name = "Azure AI Project Manager"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "ai_foundry_project_developer" {
  depends_on = [
   module.project_1
  ]
  scope                = module.project_1.PROJECT_RESOURCE_GROUP_ID
  role_definition_name = "Azure AI Developer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "ai_foundry_project_project_manager" {
  depends_on = [
    module.project_1
  ]
  scope                = module.project_1.PROJECT_RESOURCE_GROUP_ID
  role_definition_name = "Azure AI Project Manager"
  principal_id         = data.azurerm_client_config.current.object_id
}


