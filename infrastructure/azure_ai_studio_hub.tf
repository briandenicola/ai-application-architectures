resource "azurerm_machine_learning_workspace" "this" {
  count                         = var.deploy_ai_workspace == "true" ? 1 : 0
  name                          = local.machine_learning_workspace_name
  location                      = azurerm_resource_group.ml[0].location
  resource_group_name           = azurerm_resource_group.ml[0].name
  application_insights_id       = azurerm_application_insights.this.id
  key_vault_id                  = azurerm_key_vault.this.id
  storage_account_id            = azurerm_storage_account.this.id
  public_network_access_enabled = true
  identity {
    type = "SystemAssigned"
  }
}

resource "azapi_update_resource" "machine_learning_workspace_name_updates" {
  depends_on = [
    azurerm_machine_learning_workspace.this
  ]

  count       = var.deploy_ai_workspace == "true" ? 1 : 0
  type        = "Microsoft.MachineLearningServices/workspaces@2024-07-01-preview"
  resource_id = azurerm_machine_learning_workspace.this[0].id

  body = jsonencode({
    properties = {
      ipAllowlist = [
        "${chomp(data.http.myip.response_body)}"
      ]
    }
  })
}
