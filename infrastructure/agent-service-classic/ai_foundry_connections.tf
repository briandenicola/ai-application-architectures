resource "azapi_resource" "bing_to_agent_project_connection" {
  type      = "Microsoft.CognitiveServices/accounts/connections@2025-06-01"
  name      = azapi_resource.bing_grounding.name
  parent_id = azapi_resource.ai_foundry.id

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

