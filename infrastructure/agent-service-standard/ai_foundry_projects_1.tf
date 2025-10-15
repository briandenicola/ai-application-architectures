
module "project_1" {
  depends_on = [
    azapi_resource.ai_foundry,
    azurerm_private_endpoint.pe_aifoundry
  ]
  source   = "./project"

  foundry_project = {
    name          = local.project_1
    location      = local.location
    resource_name = local.resource_name
    ai_foundry_id = azapi_resource.ai_foundry.id
    tag           = var.tags
    dns = {
      search_private_dns_zone_id  = azurerm_private_dns_zone.privatelink_search_windows_net.id
      cosmos_private_dns_zone_id  = azurerm_private_dns_zone.privatelink_documents_azure_com.id
      storage_private_dns_zone_id = azurerm_private_dns_zone.privatelink_blob_core_windows_net.id
    }
    pe_subnet_id = azurerm_subnet.private-endpoints.id
    logs = {
      workspace_id = azurerm_log_analytics_workspace.this.id
    }
    models = [
    {
        name     = "gpt-4.1"
        version  = "2025-04-14"
        format = "OpenAI"
    }]
  }
}
