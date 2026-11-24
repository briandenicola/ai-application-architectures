resource "random_pet" "this" {
  length    = 1
  separator = ""
}

resource "random_id" "this" {
  byte_length = 2
}

resource "random_uuid" "guid" {}

locals {
  resource_name        = "${random_pet.this.id}-${random_id.this.dec}"
  ai_services_name     = "${local.resource_name}-foundry"
  project_name         = "${local.resource_name}-project"
  search_service_name  = "${local.project_name}-search"
  storage_account_name = "${substr(replace(random_uuid.guid.result, "-", ""), 0, 22)}sa"
  tags                 = { sample = "foundryiq", data = "synthetic" }
}

resource "azurerm_resource_group" "this" {
  name     = "${local.resource_name}-ai_rg"
  location = var.location
  tags     = local.tags
}

resource "azurerm_storage_account" "this" {
  name                            = local.storage_account_name
  resource_group_name             = azurerm_resource_group.this.name
  location                        = azurerm_resource_group.this.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = true
  tags                            = local.tags
}

resource "azapi_resource" "container" {
  type      = "Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01"
  name      = "handbook"
  parent_id = "${azurerm_storage_account.this.id}/blobServices/default"
  body = {
    properties = {
      publicAccess = "None"
    }
  }
}

resource "azurerm_search_service" "this" {
  name                          = local.search_service_name
  resource_group_name           = azurerm_resource_group.this.name
  location                      = azurerm_resource_group.this.location
  sku                           = var.search_sku
  replica_count                 = 1
  partition_count               = 1
  semantic_search_sku           = "free"
  local_authentication_enabled  = false
  public_network_access_enabled = true
  tags                          = local.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azapi_resource" "foundry" {
  type      = "Microsoft.CognitiveServices/accounts@2025-06-01"
  name      = local.ai_services_name
  parent_id = azurerm_resource_group.this.id
  location  = azurerm_resource_group.this.location
  tags      = local.tags

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "AIServices"
    sku  = { name = "S0" }
    properties = {
      allowProjectManagement = true
      customSubDomainName    = local.ai_services_name
      disableLocalAuth       = true
      publicNetworkAccess    = "Enabled"
    }
  }
}

resource "azapi_resource" "project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-06-01"
  name      = local.project_name
  parent_id = azapi_resource.foundry.id
  location  = azurerm_resource_group.this.location
  tags      = local.tags

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = {
      displayName = "Foundry IQ employee handbook"
      description = "Synthetic policies shared by Foundry and Copilot Studio."
    }
  }

  response_export_values = ["identity.principalId"]
}

resource "azapi_resource" "chat_model" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-06-01"
  name      = var.chat_model_name
  parent_id = azapi_resource.foundry.id

  depends_on = [azapi_resource.project]

  body = {
    sku = {
      name     = var.chat_model_sku
      capacity = var.chat_model_capacity
    }
    properties = {
      model = {
        format  = "OpenAI"
        name    = var.chat_model_name
        version = var.chat_model_version
      }
    }
  }
}

resource "azapi_resource" "embedding_model" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-06-01"
  name      = var.embedding_model_name
  parent_id = azapi_resource.foundry.id

  depends_on = [azapi_resource.chat_model]

  body = {
    sku = {
      name     = var.embedding_model_sku
      capacity = var.embedding_model_capacity
    }
    properties = {
      model = {
        format  = "OpenAI"
        name    = var.embedding_model_name
        version = var.embedding_model_version
      }
    }
  }

}

moved {
  from = azapi_resource.model["chat"]
  to   = azapi_resource.chat_model
}

moved {
  from = azapi_resource.model["embedding"]
  to   = azapi_resource.embedding_model
}
