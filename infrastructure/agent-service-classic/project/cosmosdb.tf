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
    azurerm_cosmosdb_account.this,
    azurerm_private_endpoint.pe_aisearch
  ]
  name                = "${azurerm_cosmosdb_account.this.name}-ep"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  subnet_id           = var.foundry_project.pe_subnet_id

  private_service_connection {
    name                           = "${azurerm_cosmosdb_account.this.name}-ep"
    private_connection_resource_id = azurerm_cosmosdb_account.this.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.documents.azure.com"
    private_dns_zone_ids = [
      var.foundry_project.dns.cosmos_private_dns_zone_id
    ]
  }
}
