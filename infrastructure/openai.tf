resource "azurerm_cognitive_account" "this" {
  name                  = local.openai_name
  resource_group_name   = azurerm_resource_group.this.name
  location              = azurerm_resource_group.this.location
  kind                  = "OpenAI"
  custom_subdomain_name = local.openai_name

  sku_name = "S0"
}
