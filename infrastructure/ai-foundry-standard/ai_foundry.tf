resource "azapi_resource" "ai_foundry" {
  depends_on = [ 
    azapi_resource.ai_search,
    azurerm_cosmosdb_account.this, 
    azurerm_storage_account.this,  
    azurerm_private_endpoint.pe_storage,
    azurerm_private_endpoint.pe_cosmosdb,
    azurerm_private_endpoint.pe_aisearch,
    azurerm_private_endpoint.pe_aifoundry    
  ]

  type                      = "Microsoft.CognitiveServices/accounts@2025-06-01"
  name                      = local.ai_services_name
  parent_id                 = azurerm_resource_group.this.id
  location                  = azurerm_resource_group.this.location
  schema_validation_enabled = false

  body = {
    kind = "AIServices",
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }

    properties = {
      disableLocalAuth = false
      allowProjectManagement = true
      customSubDomainName = local.resource_name
      publicNetworkAccess = "Disabled"
      networkAcls = {
        defaultAction = "Allow"
      }
      networkInjections = [
        {
          scenario                   = "agent"
          subnetArmId                = azurerm_subnet.agents.id
          useMicrosoftManagedNetwork = false
        }
      ]
    }
  }

  response_export_values = [
    "properties.discovery_url"
  ]
}

resource "azurerm_private_endpoint" "pe_aifoundry" {
  name                = "${azapi_resource.ai_foundry.name}-private-endpoint"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  subnet_id           = azurerm_subnet.private-endpoints.id

  private_service_connection {
    name                           = "${azapi_resource.ai_foundry.name}-private-link-service-connection"
    private_connection_resource_id = azapi_resource.ai_foundry.id
    subresource_names = ["account"]
    is_manual_connection = false
  }

  private_dns_zone_group {
    name = "${azapi_resource.ai_foundry.name}-dns-config"
    private_dns_zone_ids = [
      azurerm_private_dns_zone.privatelink_cognitiveservices_azure_com.id,
      azurerm_private_dns_zone.privatelink_services_ai_azure_com.id,
      azurerm_private_dns_zone.privatelink_openai_azure_com.id
    ]
  }
}