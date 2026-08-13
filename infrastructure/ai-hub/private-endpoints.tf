# Customer-side private endpoints. These are how users, applications and the
# Terraform agent in the spoke reach the platform. They are distinct from the
# managed private endpoints created in managed_network.tf, which are how the
# hub's own compute reaches these same resources from inside the managed VNet.
# Both sets are required.

locals {
  private_endpoints = {
    hub = {
      resource_id = azurerm_ai_foundry.this.id
      subresource = "amlworkspace"
      zones       = ["privatelink.api.azureml.ms", "privatelink.notebooks.azure.net"]
    }
    storage_blob = {
      resource_id = azurerm_storage_account.this.id
      subresource = "blob"
      zones       = ["privatelink.blob.core.windows.net"]
    }
    storage_file = {
      resource_id = azurerm_storage_account.this.id
      subresource = "file"
      zones       = ["privatelink.file.core.windows.net"]
    }
    storage_table = {
      resource_id = azurerm_storage_account.this.id
      subresource = "table"
      zones       = ["privatelink.table.core.windows.net"]
    }
    storage_queue = {
      resource_id = azurerm_storage_account.this.id
      subresource = "queue"
      zones       = ["privatelink.queue.core.windows.net"]
    }
    keyvault = {
      resource_id = azurerm_key_vault.this.id
      subresource = "vault"
      zones       = ["privatelink.vaultcore.azure.net"]
    }
    acr = {
      resource_id = azurerm_container_registry.this.id
      subresource = "registry"
      zones       = ["privatelink.azurecr.io"]
    }
  }
}

resource "azurerm_private_endpoint" "this" {
  for_each            = local.private_endpoints
  name                = "${local.resource_name}-${each.key}-pe"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  subnet_id           = azurerm_subnet.private-endpoints.id

  private_service_connection {
    name                           = "${local.resource_name}-${each.key}-psc"
    private_connection_resource_id = each.value.resource_id
    subresource_names              = [each.value.subresource]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [for z in each.value.zones : local.private_dns_zone_ids[z]]
  }
}
