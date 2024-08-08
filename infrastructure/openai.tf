resource "azurerm_cognitive_account" "this" {
  name                = local.openai_name
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  kind                = "OpenAI"

  sku_name = "S0"
}

resource "azurerm_cognitive_deployment" "gpt" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.this.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-05-13"
  }

  scale {
    type = "Standard"
  }
}

resource "azurerm_cognitive_deployment" "gpt4_turbo" {
  name                 = "gpt-4-turbo"
  cognitive_account_id = azurerm_cognitive_account.this.id
  model {
    format  = "OpenAI"
    name    = "gpt-4"
    version = "vision-preview"
  }

  scale {
    type = "Standard"
    capacity = 20
  }
}