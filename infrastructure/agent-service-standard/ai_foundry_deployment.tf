resource "azurerm_cognitive_deployment" "gpt_4o" {
  depends_on = [
    azapi_resource.ai_foundry_project
  ]
  
  name                 = "gpt-4o"
  cognitive_account_id = azapi_resource.ai_foundry.id

  sku {
    name     = "GlobalStandard"
    capacity = 1
  }

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-11-20"
  }
}
