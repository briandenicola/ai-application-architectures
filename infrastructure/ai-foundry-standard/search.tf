resource "azapi_resource" "ai_search" {
  type                      = "Microsoft.Search/searchServices@2025-05-01"
  name                      = local.search_service_name
  parent_id                 = azurerm_resource_group.this.id
  location                  = azurerm_resource_group.this.location
  schema_validation_enabled = true

  body = {
    sku = {
      name = "standard"
    }

    identity = {
      type = "SystemAssigned"
    }

    properties = {
      replicaCount     = 1
      partitionCount   = 1
      hostingMode      = "default"
      semanticSearch   = "disabled"
      disableLocalAuth = false
      authOptions = {
        aadOrApiKey = {
          aadAuthFailureMode = "http401WithBearerChallenge"
        }
      }

      publicNetworkAccess = "Disabled"
      networkRuleSet = {
        bypass = "None"
      }
    }
  }
}

resource "azurerm_private_endpoint" "pe_aisearch" {
  depends_on = [
    azapi_resource.ai_search,
    azurerm_private_endpoint.pe_storage
  ]
  name                = "${azapi_resource.ai_search.name}-ep"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  subnet_id           = azurerm_subnet.private-endpoints.id

  private_service_connection {
    name                           = "${azapi_resource.ai_search.name}-ep"
    private_connection_resource_id = azapi_resource.ai_search.id
    subresource_names              = ["searchService"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = azurerm_private_dns_zone.privatelink_search_windows_net.name
    private_dns_zone_ids = [azurerm_private_dns_zone.privatelink_search_windows_net.id]
  }
}
