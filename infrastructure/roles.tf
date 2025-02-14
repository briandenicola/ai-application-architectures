
resource "azurerm_role_assignment" "this" {
  scope                            = azurerm_cognitive_account.this.id
  role_definition_name             = "Cognitive Services OpenAI User"
  principal_id                     = data.azurerm_client_config.current.object_id
}
