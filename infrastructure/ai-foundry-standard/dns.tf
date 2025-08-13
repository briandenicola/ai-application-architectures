resource "azurerm_private_dns_zone" "privatelink_documents_azure_com" {
  name                = "privatelink.documents.azure.com"
  resource_group_name = azurerm_resource_group.core.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "privatelink_documents_azure_com" {
  name                  = "${azurerm_virtual_network.this.name}-link"
  private_dns_zone_name = azurerm_private_dns_zone.privatelink_documents_azure_com.name
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

resource "azurerm_private_dns_zone" "privatelink_blob_core_windows_net" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = azurerm_resource_group.core.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "privatelink_blob_core_windows_net" {
  name                  = "${azurerm_virtual_network.this.name}-link"
  private_dns_zone_name = azurerm_private_dns_zone.privatelink_blob_core_windows_net.name
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

resource "azurerm_private_dns_zone" "privatelink_queue_core_windows_net" {
  name                = "privatelink.queue.core.windows.net"
  resource_group_name = azurerm_resource_group.core.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "privatelink_queue_core_windows_net" {
  name                  = "${azurerm_virtual_network.this.name}-link"
  private_dns_zone_name = azurerm_private_dns_zone.privatelink_queue_core_windows_net.name
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

resource "azurerm_private_dns_zone" "privatelink_file_core_windows_net" {
  name                = "privatelink.file.core.windows.net"
  resource_group_name = azurerm_resource_group.core.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "privatelink_file_core_windows_net" {
  name                  = "${azurerm_virtual_network.this.name}-link"
  private_dns_zone_name = azurerm_private_dns_zone.privatelink_file_core_windows_net.name
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

resource "azurerm_private_dns_zone" "privatelink_table_core_windows_net" {
  name                = "privatelink.table.core.windows.net"
  resource_group_name = azurerm_resource_group.this.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "privatelink_table_core_windows_net" {
  name                  = "${azurerm_virtual_network.this.name}-link"
  private_dns_zone_name = azurerm_private_dns_zone.privatelink_table_core_windows_net.name
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

resource "azurerm_private_dns_zone" "privatelink_cognitiveservices_azure_com" {
  name                = "privatelink.cognitiveservices.azure.com"
  resource_group_name = azurerm_resource_group.core.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "privatelink_cognitiveservices_azure_com" {
  name                  = "${azurerm_virtual_network.this.name}-link"
  private_dns_zone_name = azurerm_private_dns_zone.privatelink_cognitiveservices_azure_com.name
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

resource "azurerm_private_dns_zone" "privatelink_openai_azure_com" {
  name                = "privatelink.openai.azure.com"
  resource_group_name = azurerm_resource_group.core.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "privatelink_openai_azure_com" {
  name                  = "${azurerm_virtual_network.this.name}-link"
  private_dns_zone_name = azurerm_private_dns_zone.privatelink_openai_azure_com.name
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

resource "azurerm_private_dns_zone" "privatelink_services_ai_azure_com" {
  name                = "privatelink.services.ai.azure.com"
  resource_group_name = azurerm_resource_group.core.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "privatelink_services_ai_azure_com" {
  name                  = "${azurerm_virtual_network.this.name}-link"
  private_dns_zone_name = azurerm_private_dns_zone.privatelink_services_ai_azure_com.name
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

resource "azurerm_private_dns_zone" "privatelink_api_azureml_ms" {
  name                = "privatelink.api.azureml.ms"
  resource_group_name = azurerm_resource_group.core.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "privatelink_api_azureml_ms" {
  name                  = "${azurerm_virtual_network.this.name}-link"
  private_dns_zone_name = azurerm_private_dns_zone.privatelink_api_azureml_ms.name
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

resource "azurerm_private_dns_zone" "privatelink_search_windows_net" {
  name                = "privatelink.search.windows.net"
  resource_group_name = azurerm_resource_group.core.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "privatelink_search_windows_net" {
  name                  = "${azurerm_virtual_network.this.name}-link"
  private_dns_zone_name = azurerm_private_dns_zone.privatelink_search_windows_net.name
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

