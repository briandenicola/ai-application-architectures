resource "azapi_resource" "ai_foundry" {
  type      = "Microsoft.CognitiveServices/accounts@2025-10-01-preview"
  name      = local.ai_services_name
  parent_id = azurerm_resource_group.this.id
  location  = azurerm_resource_group.this.location
  #schema_validation_enabled = false

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "AIServices"
    sku = {
      name = "S0"
    }

    properties = {
      disableLocalAuth       = true
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

resource "time_sleep" "wait_ai_foundry" {
  create_duration = "10m"

  depends_on = [
    azapi_resource.ai_foundry
  ]
}

resource "azapi_resource" "managed_network" {
  type      = "Microsoft.CognitiveServices/accounts/managedNetworks@2025-10-01-preview"
  name      = "default"
  parent_id = azapi_resource.ai_foundry.id

  schema_validation_enabled = false

  body = {
    properties = {
      managedNetwork = {
        isolationMode       = var.managed_network_isolation_mode
        managedNetworkKind  = "V2"
        provisionNetworkNow = true
      }
    }
  }

  depends_on = [
    time_sleep.wait_ai_foundry
  ]
}


# Outbound rules allow the managed VNet, where hosted agents run, to reach
# endpoints that are otherwise blocked or private. The managed network API does
# not reliably support concurrent outbound rule creation, so apply with
# -parallelism=1 when creating multiple rules.

resource "azurerm_role_assignment" "foundry_network_connection_approver" {
  scope                = azurerm_resource_group.this.id
  role_definition_name = "Azure AI Enterprise Network Connection Approver"
  principal_id         = azapi_resource.ai_foundry.identity[0].principal_id
}

resource "azapi_resource" "aiservices_outbound_rule" {
  type      = "Microsoft.CognitiveServices/accounts/managedNetworks/outboundRules@2025-10-01-preview"
  name      = "aiservices-account-rule"
  parent_id = azapi_resource.managed_network.id

  schema_validation_enabled = false

  body = {
    properties = {
      type = "PrivateEndpoint"
      destination = {
        serviceResourceId = azapi_resource.ai_foundry.id
        subresourceTarget = "account"
      }
      category = "UserDefined"
    }
  }

  depends_on = [
    azapi_resource.managed_network,
    azurerm_role_assignment.foundry_network_connection_approver
  ]
}

resource "azapi_resource" "managed_network_fqdn_outbound_rules" {
  for_each  = var.managed_network_fqdn_outbound_rules
  type      = "Microsoft.CognitiveServices/accounts/managedNetworks/outboundRules@2025-10-01-preview"
  name      = each.key
  parent_id = azapi_resource.managed_network.id

  schema_validation_enabled = false

  body = {
    properties = {
      type        = "FQDN"
      destination = each.value.destination.fqdn
      category    = "UserDefined"
    }
  }

  depends_on = [
    azapi_resource.aiservices_outbound_rule
  ]
}

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

  depends_on = [
    time_sleep.wait_ai_foundry
  ]
}