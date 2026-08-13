# Private DNS. Without these zones the private endpoints resolve to their public
# A records and traffic silently leaves the VNet, which defeats the entire
# lockdown. Create locally only when central zones are not supplied.

locals {
  private_dns_zones = toset([
    "privatelink.api.azureml.ms",
    "privatelink.notebooks.azure.net",
    "privatelink.blob.core.windows.net",
    "privatelink.file.core.windows.net",
    "privatelink.table.core.windows.net",
    "privatelink.queue.core.windows.net",
    "privatelink.vaultcore.azure.net",
    "privatelink.azurecr.io",
    "privatelink.cognitiveservices.azure.com",
    "privatelink.openai.azure.com",
    "privatelink.services.ai.azure.com",
    "privatelink.monitor.azure.com",
    "privatelink.oms.opinsights.azure.com",
    "privatelink.ods.opinsights.azure.com",
    "privatelink.agentsvc.azure-automation.net",
  ])

  private_dns_zone_ids =  {
    for z in local.private_dns_zones : z => azurerm_private_dns_zone.this[z].id
  } 
}

resource "azurerm_private_dns_zone" "this" {
  for_each            = local.private_dns_zones
  name                = each.key
  resource_group_name = azurerm_resource_group.core.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "this" {
  for_each              = local.private_dns_zones
  name                  = "${local.resource_name}-link-${each.key}"
  resource_group_name   = azurerm_resource_group.core.name
  private_dns_zone_name = azurerm_private_dns_zone.this[each.key].name
  virtual_network_id    = azurerm_virtual_network.this.id
  registration_enabled  = false
}
