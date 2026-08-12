
module "project_1" {
  depends_on = [
    azapi_resource.ai_foundry,
  ]
  source = "./project"

  foundry_project = {
    name          = local.project_name
    location      = local.location
    resource_name = local.resource_name
    tag           = var.tags

    resource_group = {
      name = azurerm_resource_group.this.name
      id   = azurerm_resource_group.this.id
    }

    ai_foundry = {
      id   = azapi_resource.ai_foundry.id
      name = azapi_resource.ai_foundry.name
    }

    logs = {
      workspace_id = azurerm_log_analytics_workspace.this.id
    }

    models = [
      {
        name     = "snowflake--snowflake-arctic-embed-l-v2"
        sku      = "A100_80GB"
        capacity = 1
        model    = "azureml://registries/azure-huggingface/models/snowflake--snowflake-arctic-embed-l-v2.0/versions/1"
        template = "azureml://registries/azure-huggingface/deploymenttemplates/snowflake--snowflake-arctic-embed-l-v20--nvidia-a100/labels/latest"
      },
      {
        name     = "nvidia--nvidia-nemotron-3-nano-30b-a3b-fp8"
        sku      = "H100_80GB"
        capacity = 1
        model    = "azureml://registries/azure-huggingface/models/nvidia--nvidia-nemotron-3-nano-30b-a3b-fp8/versions/3"        
        template = "azureml://registries/azure-huggingface/deploymenttemplates/nvidia--nvidia-nemotron-3-nano-30b-a3b-fp8--256k-nvidia-h100/labels/latest"
      }
    ]
  }
}
