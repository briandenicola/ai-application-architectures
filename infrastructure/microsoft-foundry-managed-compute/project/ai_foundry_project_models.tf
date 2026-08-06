resource "azapi_resource" "arctic_embed_managed_compute" {
  type                      = "Microsoft.CognitiveServices/accounts/managedComputeDeployments@2026-05-15-preview"
  name                      = var.foundry_project.models[0].name
  parent_id                 = var.foundry_project.ai_foundry.id
  schema_validation_enabled = false

  body = {
    sku = {
      name     = "GlobalManagedCompute"
      capacity = var.foundry_project.models[0].capacity
    }
    properties = {
      acceleratorType    = var.foundry_project.models[0].sku
      deploymentTemplate = var.foundry_project.models[0].template
      model              = var.foundry_project.models[0].model
    }
  }

  response_export_values = ["*"]

  timeouts {
    create = "60m"
    update = "60m"
    delete = "60m"
  }

  depends_on = [
    azapi_resource.ai_foundry_project,
  ]
}
