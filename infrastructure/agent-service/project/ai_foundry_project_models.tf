resource "azapi_resource" "model_deployments" {
  count     = length(var.foundry_project.models)
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-06-01"
  name      = var.foundry_project.models[count.index].name
  parent_id = var.foundry_project.ai_foundry.id

  body = {
    properties = {
      model = {
        format  = var.foundry_project.models[count.index].format
        name    = var.foundry_project.models[count.index].name
        version = var.foundry_project.models[count.index].version
      }
    }
    sku = {
      name     = "GlobalStandard"
      capacity = 250
    }
  }
}
