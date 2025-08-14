resource "azapi_resource" "ai_foundry" {
  depends_on = [
    azapi_resource.ai_search,
    azurerm_cosmosdb_account.this,
    azurerm_storage_account.this,    
    azurerm_private_endpoint.pe_storage,
    azurerm_private_endpoint.pe_cosmosdb,
    azurerm_private_endpoint.pe_aisearch,
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
      disableLocalAuth       = false
      allowProjectManagement = true
      customSubDomainName    = local.resource_name
      publicNetworkAccess    = "Disabled"
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
    "properties.endpoint"
  ]
}

resource "azurerm_private_endpoint" "pe_aifoundry" {
  depends_on = [
    azapi_resource.ai_foundry
  ]
  name                = "${azapi_resource.ai_foundry.name}-ep"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  subnet_id           = azurerm_subnet.private-endpoints.id

  private_service_connection {
    name                           = "${azapi_resource.ai_foundry.name}-ep"
    private_connection_resource_id = azapi_resource.ai_foundry.id
    subresource_names              = ["account"]
    is_manual_connection           = false
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

data "azurerm_monitor_diagnostic_categories" "ai" {
  resource_id = azapi_resource.ai_foundry.id
}

resource "azurerm_monitor_diagnostic_setting" "ai" {
  depends_on = [
    data.azurerm_monitor_diagnostic_categories.ai
  ]
  name                       = "diag"
  target_resource_id         = azapi_resource.ai_foundry.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.ai.log_category_types)
    content {
      category = enabled_log.value
    }
  }

  enabled_metric {
    category = "AllMetrics"
  }
}