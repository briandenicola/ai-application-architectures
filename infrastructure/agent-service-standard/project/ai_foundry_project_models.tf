resource "azapi_resource" "model_deployments" {
  count    = length(var.foundry_project.models)    
  type      = "Microsoft.CognitiveServices/accounts/projects/deployments@2025-06-01"
  name      = var.foundry_project.models[count.index].name
  parent_id = data.azurerm_cognitive_account.this.id

  body = {
    properties = {
      model = {
        format = var.foundry_project.models[count.index].format
        name   = var.foundry_project.models[count.index].name
        version = var.foundry_project.models[count.index].version
      }
    }
    sku = {
      name     = "GlobalStandard"
      capacity = 250
    } 
  }
}