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
