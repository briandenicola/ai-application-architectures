resource "azurerm_cognitive_deployment" "gpt_ai_services" {
  name                 = "gpt-4.1.2"
  cognitive_account_id = data.azurerm_cognitive_account.global.id
  model {
    format  = "OpenAI"
    name    = "gpt-4.1"
    version = "2025-04-14"
  }

  sku {
    name     = "GlobalStandard"
    capacity = 10
  }
}

resource "azurerm_cognitive_deployment" "o1" {
  name                 = "o1"
  cognitive_account_id = azapi_resource.global.id
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