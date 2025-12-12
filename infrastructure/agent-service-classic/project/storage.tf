resource "azurerm_storage_account" "this" {

  name                = local.storage_account_name
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location

  account_kind              = "StorageV2"
  account_tier              = "Standard"
  account_replication_type  = "ZRS"
  shared_access_key_enabled = true

  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  network_rules {
    default_action = "Deny"
    bypass = [
      "AzureServices"
    ]
  }
}

resource "azurerm_private_endpoint" "pe_storage" {
  depends_on = [
    azurerm_storage_account.this,
  ]

  name                = "${azurerm_storage_account.this.name}-ep"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  subnet_id           = var.foundry_project.pe_subnet_id

  private_service_connection {
    name                           = "${azurerm_storage_account.this.name}-ep"
    private_connection_resource_id = azurerm_storage_account.this.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.blob.core.windows.net"
    private_dns_zone_ids = [
      var.foundry_project.dns.storage_private_dns_zone_id
    ]
  }
}
