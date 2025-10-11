
module "projects" {
  depends_on = [
    azapi_resource.ai_foundry,
    azurerm_private_endpoint.pe_aifoundry
  ]
  for_each = toset(local.projects)
  source   = "./project"

  foundry_project = {
    name          = each.value
    location      = local.location
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
        name     = "gpt-4o"
        version  = "2024-11-20"
        sku_type = "OpenAI"
    },
    {
        name     = "o1"
        version  = "2024-12-17"
        sku_type = "OpenAI"
    }]
  }
}
