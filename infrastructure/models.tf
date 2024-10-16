resource "azurerm_cognitive_deployment" "gpt" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.this.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-05-13"
  }

  sku {
    name = "Standard"
  }
}

resource "azurerm_cognitive_deployment" "gpt_35_turbo" {
  name                 = "gpt-35-turbo"
  cognitive_account_id = azurerm_cognitive_account.this.id
  model {
    format  = "OpenAI"
    name    = "gpt-35-turbo"
    version = "1106"
  }

  sku {
    name     = "Standard"
    capacity = 10

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

  sku {
    name     = "Standard"
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

resource "azurerm_cognitive_deployment" "gpt_35_turbo_embedding" {
  name                 = "gpt-35-turbo"
  cognitive_account_id = azurerm_cognitive_account.embedding.id
  model {
    format  = "OpenAI"
    name    = "gpt-35-turbo"
    version = "1106"
  }

  sku {
    name     = "Standard"
    capacity = 10

  }
}
