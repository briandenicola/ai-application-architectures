
module "project_1" {
  depends_on = [
    azapi_resource.ai_foundry,
  ]
  source   = "./project"

  foundry_project = {
    name          = local.project_name
    location      = local.location
    resource_name = local.resource_name
    tag           = var.tags

    resource_group= {
      name = azurerm_resource_group.this.name
      id   = azurerm_resource_group.this.id
    }

    ai_foundry    = {
      id = azapi_resource.ai_foundry.id
      name = azapi_resource.ai_foundry.name
    }

    logs          = {
      workspace_id = azurerm_log_analytics_workspace.this.id
    }

    models        = [
    {
        name     = "gpt-4.1"
        version  = "2025-04-14"
        format = "OpenAI"
    }]
  }
}
