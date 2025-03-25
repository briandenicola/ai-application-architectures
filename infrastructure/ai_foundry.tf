resource "azurerm_ai_foundry" "this" {
  depends_on          = [azurerm_role_assignment.key_user, azurerm_role_assignment.storage_owner]
  name                = local.hub_name
  location            = local.location
  resource_group_name = azurerm_resource_group.this.name
  storage_account_id  = azurerm_storage_account.this.id
  key_vault_id        = azurerm_key_vault.this.id

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_ai_foundry_project" "this" {
  name               = local.project_name
  location           = azurerm_ai_foundry.this.location
  ai_services_hub_id = azurerm_ai_foundry.this.id

  identity {
    type = "SystemAssigned"
  }
}
