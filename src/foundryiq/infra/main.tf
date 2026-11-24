resource "random_pet" "this" {
  length    = 1
  separator = ""
}

resource "random_id" "this" {
  byte_length = 3
}

locals {
  suffix       = "${random_pet.this.id}-${random_id.this.hex}"
  account_name = "ai-${local.suffix}"
  project_name = "project-${local.suffix}"
  tags         = { sample = "foundryiq", data = "synthetic" }
  models = {
    chat = {
      name     = var.chat_model_name
      version  = var.chat_model_version
      sku      = var.chat_model_sku
      capacity = var.chat_model_capacity
    }
    embedding = {
      name     = var.embedding_model_name
      version  = var.embedding_model_version
      sku      = var.embedding_model_sku
      capacity = var.embedding_model_capacity
    }
  }
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.suffix}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_storage_account" "this" {
  name                            = "st${substr(random_pet.this.id, 0, 12)}${random_id.this.hex}"
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
  name                          = "search-${local.suffix}"
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
  name      = local.account_name
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
      customSubDomainName    = local.account_name
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

resource "azapi_resource" "model" {
  for_each  = local.models
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-06-01"
  name      = each.key
  parent_id = azapi_resource.foundry.id

  body = {
    sku = {
      name     = each.value.sku
      capacity = each.value.capacity
    }
    properties = {
      model = {
        format  = "OpenAI"
        name    = each.value.name
        version = each.value.version
      }
    }
  }
}
