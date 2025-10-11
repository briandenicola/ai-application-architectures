resource "azapi_resource" "deepseek_r1_deployment" {    
    depends_on = [
      data.azurerm_cognitive_account.this,
      azurerm_cognitive_deployment.text_embedding_3_large
    ]
    type      = "Microsoft.CognitiveServices/accounts/deployments@2024-10-01"
    name      = "deepseek-r1"
    parent_id = data.azurerm_cognitive_account.this.id

    body = {
        properties = {
            model = {
                format = "DeepSeek"
                name   = "DeepSeek-R1"
                version = "1"
            }
        }
        sku = {
            name     = "GlobalStandard"
            capacity = 250
        }
    }
}

resource "azapi_resource" "phi_4_deployment" {    
    depends_on = [
      data.azurerm_cognitive_account.this,
      azapi_resource.deepseek_r1_deployment
    ]
    type      = "Microsoft.CognitiveServices/accounts/deployments@2024-10-01"
    name      = "phi-4"
    parent_id = data.azurerm_cognitive_account.this.id

    body = {
        properties = {
            model = {
                format  = "Microsoft"
                name    = "Phi-4"
                version = "7"
            }
        }
        sku = {
            name     = "GlobalStandard"
            capacity = 1
        }
    }
}