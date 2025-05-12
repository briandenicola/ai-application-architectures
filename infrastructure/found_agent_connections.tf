resource "azapi_resource" "llm_to_agent_project_connection" {
  type      = "Microsoft.MachineLearningServices/workspaces/connections@2025-01-01-preview"
  name      = "Hub-to-AIServices"
  parent_id = azurerm_ai_foundry.this.id
  body = {
    properties = {
      category      = "AIServices"
      isSharedToAll = true
      metadata = {
        ApiType    = "Azure"
        ResourceId = data.azurerm_cognitive_account.global.id
        Location   = data.azurerm_cognitive_account.global.location
      }
      target   = data.azurerm_cognitive_account.global.id
      authType = "ApiKey"
      credentials = {
        key = data.azurerm_cognitive_account.global.primary_access_key
      }
    }
  }
}

resource "azapi_resource" "bing_to_agent_project_connection" {
  type      = "Microsoft.MachineLearningServices/workspaces/connections@2025-01-01-preview"
  name      = "Hub-to-BingGrounding"
  parent_id = azurerm_ai_foundry.this.id

  body = {
    properties = {
      category      = "ApiKey"
      authType      = "ApiKey"
      isSharedToAll = true
      metadata = {
        ApiType    = "Azure"
        ResourceId = azapi_resource.bing_grounding.id
        type       = "bing_grounding"
      }
      target   = "${azapi_resource.bing_grounding.output.properties.endpoint}"
      credentials = {
        key = data.azapi_resource_action.bing_keys.output.key1
      }
    }
  }
}

# data "azapi_resource_action" "rotate_openai_key1" {
#   type        = "Microsoft.Bing/accounts@2025-05-01-preview"
#   resource_id = azapi_resource.bing_grounding.id
#   action      = "regenerateKey"
#   method      = "POST"

#   body = {
#     keyName = "Key1"
#   }

#   response_export_values = ["*"]
# }