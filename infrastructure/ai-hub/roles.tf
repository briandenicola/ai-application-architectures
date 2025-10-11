resource "azurerm_role_assignment" "regional" {
  scope                            = azurerm_cognitive_account.regional.id
  role_definition_name             = "Cognitive Services OpenAI User"
  principal_id                     = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "embedding" {
  scope                            = azurerm_cognitive_account.embedding.id
  role_definition_name             = "Cognitive Services OpenAI User"
  principal_id                     = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "global" {
  scope                            = data.azurerm_cognitive_account.global.id
  role_definition_name             = "Cognitive Services OpenAI User"
  principal_id                     = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "key_user" {
  scope                            = azurerm_key_vault.this.id
  role_definition_name             = "Key Vault Crypto Officer"
  principal_id                     = data.azurerm_client_config.current.object_id 
}

resource "azurerm_role_assignment" "storage_owner" {
  scope                            = azurerm_storage_account.this.id
  role_definition_name             = "Storage Blob Data Owner"
  principal_id                     = data.azurerm_client_config.current.object_id
  depends_on                      = [azurerm_storage_account.this]
}