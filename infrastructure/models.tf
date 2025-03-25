resource "azurerm_cognitive_deployment" "gpt" {
  name                 = "gpt-4o"
  cognitive_account_id = data.azurerm_cognitive_account.global.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-05-13"
  }

  sku {
    name     = "GlobalStandard"
    capacity = 10
  }
}
resource "azurerm_cognitive_deployment" "gpt4_vision" {
  name                 = "gpt4-vision"
  cognitive_account_id = azurerm_cognitive_account.regional.id
  model {
    format  = "OpenAI"
    name    = "gpt-4"
    version = "vision-preview"
  }

  sku {
    name     = "Standard"
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

resource "azurerm_cognitive_deployment" "text_embedding3_small" {
  name                 = "text-embedding-3-small"
  cognitive_account_id = azurerm_cognitive_account.embedding.id
  model {
    format  = "OpenAI"
    name    = "text-embedding-3-small"
    version = "1"
  }

  sku {
    name = "Standard"
  }
}

resource "azurerm_cognitive_deployment" "gpt4_embedding" {
  name                 = "gpt-4"
  cognitive_account_id = azurerm_cognitive_account.embedding.id
  model {
    format  = "OpenAI"
    name    = "gpt-4"
    version = "0613"
  }

  sku {
    name     = "Standard"
    capacity = 10
  }
}
