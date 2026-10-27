locals {
  container_app_names = { for role in ["banking", "gateway"] : role => "ca-${role}-${local.name}" }
  gateway_hostname    = "${local.container_app_names.gateway}.${azurerm_container_app_environment.functions.default_domain}"
  banking_hostname    = "${local.container_app_names.banking}.internal.${azurerm_container_app_environment.functions.default_domain}"
  storage_services    = toset(["blob", "queue", "table"])
  storage_endpoints = {
    for pair in setproduct(["banking", "gateway"], local.storage_services) :
    "${pair[0]}-${pair[1]}" => { role = pair[0], service = pair[1] }
  }
}

resource "azurerm_virtual_network" "functions" {
  name                = "vnet-${local.name}"
  resource_group_name = azurerm_resource_group.demo.name
  location            = azurerm_resource_group.demo.location
  address_space       = ["10.42.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "container_apps" {
  name                 = "container-apps"
  resource_group_name  = azurerm_resource_group.demo.name
  virtual_network_name = azurerm_virtual_network.functions.name
  address_prefixes     = ["10.42.0.0/24"]

  delegation {
    name = "container-apps"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "private_endpoints" {
  name                              = "private-endpoints"
  resource_group_name               = azurerm_resource_group.demo.name
  virtual_network_name              = azurerm_virtual_network.functions.name
  address_prefixes                  = ["10.42.1.0/24"]
  private_endpoint_network_policies = "Disabled"
}

resource "azurerm_private_dns_zone" "storage" {
  for_each            = local.storage_services
  name                = "privatelink.${each.key}.core.windows.net"
  resource_group_name = azurerm_resource_group.demo.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "storage" {
  for_each             = local.storage_services
  name                 = "functions"
  private_dns_zone_id  = azurerm_private_dns_zone.storage[each.key].id
  virtual_network_id   = azurerm_virtual_network.functions.id
  registration_enabled = false
  tags                 = local.tags
}

resource "azurerm_private_endpoint" "storage" {
  for_each            = local.storage_endpoints
  name                = "pe-${each.key}-${local.name}"
  resource_group_name = azurerm_resource_group.demo.name
  location            = azurerm_resource_group.demo.location
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.tags

  private_service_connection {
    name                           = each.key
    private_connection_resource_id = azurerm_storage_account.functions[each.value.role].id
    subresource_names              = [each.value.service]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "storage"
    private_dns_zone_ids = [azurerm_private_dns_zone.storage[each.value.service].id]
  }
}

resource "azurerm_container_app_environment" "functions" {
  name                     = "cae-${local.name}"
  resource_group_name      = azurerm_resource_group.demo.name
  location                 = azurerm_resource_group.demo.location
  infrastructure_subnet_id = azurerm_subnet.container_apps.id
  public_network_access    = "Enabled"
  tags                     = local.tags

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

resource "azurerm_container_registry" "functions" {
  name                          = "cr${substr(sha256(local.name), 0, 20)}"
  resource_group_name           = azurerm_resource_group.demo.name
  location                      = azurerm_resource_group.demo.location
  sku                           = "Basic"
  admin_enabled                 = false
  public_network_access_enabled = true
  tags                          = local.tags
}

resource "azurerm_role_assignment" "image_pull" {
  for_each             = azurerm_user_assigned_identity.function
  scope                = azurerm_container_registry.functions.id
  role_definition_name = "AcrPull"
  principal_id         = each.value.principal_id
  principal_type       = "ServicePrincipal"
}

# AzureRM does not expose kind=functionapp; use the native Microsoft.App API.
resource "azapi_resource" "functions" {
  for_each  = var.function_image == null ? toset([]) : toset(["banking", "gateway"])
  type      = "Microsoft.App/containerApps@2025-07-01"
  name      = local.container_app_names[each.key]
  parent_id = azurerm_resource_group.demo.id
  location  = azurerm_resource_group.demo.location
  tags      = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.function[each.key].id]
  }

  body = {
    kind = "functionapp"
    properties = {
      environmentId       = azurerm_container_app_environment.functions.id
      workloadProfileName = "Consumption"
      configuration = {
        activeRevisionsMode = "Single"
        ingress = {
          external      = each.key == "gateway"
          targetPort    = 80
          transport     = "auto"
          allowInsecure = false
          traffic       = [{ latestRevision = true, weight = 100 }]
        }
        registries = [{
          server   = azurerm_container_registry.functions.login_server
          identity = azurerm_user_assigned_identity.function[each.key].id
        }]
      }
      template = {
        containers = [{
          name      = "functions"
          image     = var.function_image
          resources = { cpu = 0.5, memory = "1Gi" }
          env = [for name, value in merge(local.function_storage_settings[each.key], {
            APP_ROLE                      = each.key
            AZURE_CLIENT_ID               = azurerm_user_assigned_identity.function[each.key].client_id
            AzureWebJobsStorage__clientId = azurerm_user_assigned_identity.function[each.key].client_id
            AzureFunctionsWebHost__hostid = "${each.key}-${substr(sha256(local.name), 0, 20)}"
            FUNCTIONS_WORKER_RUNTIME      = "node"
            }, each.key == "banking" ? {
            HOLDS_BLOB_URL = azurerm_storage_account.functions["banking"].primary_blob_endpoint
            } : {
            BANKING_URL              = "https://${local.banking_hostname}"
            FOUNDRY_PROJECT_ENDPOINT = local.project_endpoint
            FOUNDRY_AGENT_NAME       = local.investigator
          }) : { name = name, value = value }]
        }]
        scale = { minReplicas = 1, maxReplicas = 5 }
      }
    }
  }

  depends_on = [
    azurerm_private_endpoint.storage,
    azurerm_private_dns_zone_virtual_network_link.storage,
    azurerm_role_assignment.function_storage,
    azurerm_role_assignment.function_diagnostics,
    azurerm_role_assignment.gateway_foundry,
    azurerm_role_assignment.image_pull,
    azurerm_storage_container.holds,
  ]
}
