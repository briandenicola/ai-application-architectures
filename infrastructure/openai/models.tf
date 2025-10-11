resource "azurerm_cognitive_deployment" "gpt" {
  name                 = "gpt-4.1"
  cognitive_account_id = azurerm_cognitive_account.this.id
  model {
    format  = "OpenAI"
    name    = "gpt-4.1"
    version = "2025-04-14"
  }

  sku {
    name = "GlobalStandard"
    capacity = 10
  }
}

resource "azurerm_cognitive_deployment" "o1" {
  name                 = "o1"
  cognitive_account_id = azurerm_cognitive_account.this.id
  model {
    format  = "OpenAI"
    name    = "o1"
    version = "2024-12-17"
  }

  sku {
    name     = "GlobalStandard"
    capacity = 10
  }
}
