resource "azapi_resource" "ai_foundry" {
  type      = "Microsoft.CognitiveServices/accounts@2025-10-01-preview"
  name      = local.ai_services_name
  parent_id = azurerm_resource_group.this.id
  location  = azurerm_resource_group.this.location
  #schema_validation_enabled = false

  body = {
    kind = "AIServices"
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }

    properties = {
      disableLocalAuth       = false
      allowProjectManagement = true
      publicNetworkAccess    = "Disabled"
      customSubDomainName    = local.ai_services_name
      networkInjections = [
        {
          scenario                   = "agent"
          subnetArmId                = ""
          useMicrosoftManagedNetwork = true
        }
      ]
      networkAcls = {
        defaultAction       = "Deny"
        virtualNetworkRules = []
        ipRules             = []
      }
    }
  }

  response_export_values = [
    "properties.endpoint"
  ]
}

# Role Assignment: Network Connection Approver for AI Foundry Account Identity
# This role is required for the AI Foundry account to approve managed network private endpoint connections
# resource "azurerm_role_assignment" "foundry_network_connection_approver" {
#   depends_on          = [azapi_resource.ai_foundry]  
#   scope                = azurerm_resource_group.this.id
#   role_definition_name = "Azure AI Enterprise Network Connection Approver"
#   principal_id         = azapi_resource.ai_foundry.identity[0].principal_id
# }

# Private Endpoint for AI Foundry
resource "azurerm_private_endpoint" "cognitive_services" {
  name                = "${local.ai_services_name}-pe"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  subnet_id           = azurerm_subnet.private-endpoints.id

  private_service_connection {
    name                           = "${local.ai_services_name}-psc"
    private_connection_resource_id = azapi_resource.ai_foundry.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  dynamic "private_dns_zone_group" {
    for_each = var.enable_dns ? [1] : []
    content {
      name = "cognitive-services-dns-zone-group"
      private_dns_zone_ids = [
        azurerm_private_dns_zone.cognitive_services.id,
        azurerm_private_dns_zone.openai.id,
        azurerm_private_dns_zone.aifoundry_api.id,        
        azurerm_private_dns_zone.aifoundry_services.id
      ]
    }
  }
}