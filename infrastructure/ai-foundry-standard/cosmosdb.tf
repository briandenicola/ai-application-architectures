resource "azurerm_cosmosdb_account" "this" {
  name                = local.cosmosdb_name
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location


  offer_type                       = "Standard"
  kind                             = "GlobalDocumentDB"
  free_tier_enabled                = false
  local_authentication_disabled    = false
  public_network_access_enabled    = false
  automatic_failover_enabled       = false
  multiple_write_locations_enabled = false

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.this.location
    failover_priority = 0
    zone_redundant    = false
  }
}

resource "azurerm_private_endpoint" "pe_cosmosdb" {
  depends_on = [
    azapi_resource.ai_search,
    azurerm_private_endpoint.pe_aisearch
  ]
  name                = "${azurerm_cosmosdb_account.this.name}-ep"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  subnet_id           = azurerm_subnet.private-endpoints.id

  private_service_connection {
    name                           = "${azurerm_cosmosdb_account.this.name}-ep"
    private_connection_resource_id = azurerm_cosmosdb_account.this.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = azurerm_private_dns_zone.privatelink_documents_azure_com.name
    private_dns_zone_ids = [azurerm_private_dns_zone.privatelink_documents_azure_com.id]
  }
}
