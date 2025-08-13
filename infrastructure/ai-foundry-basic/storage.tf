resource "azurerm_storage_account" "this" {
  name                      = local.storage_account_name
  resource_group_name       = azurerm_resource_group.core.name
  location                  = azurerm_resource_group.core.location
  account_tier              = "Standard"
  account_replication_type  = "LRS"
  account_kind              = "StorageV2"
  min_tls_version           = "TLS1_2"
}
