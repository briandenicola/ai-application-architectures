resource "random_pet" "name" {
  length = 2
}

resource "random_id" "suffix" {
  byte_length = 3
}

locals {
  name = "${random_pet.name.id}-${random_id.suffix.hex}"
  tags = {
    environment = "demo"
    workload    = "mcp-ui-apps"
    managed-by  = "terraform"
  }
  # Stable built-in ID; Azure AI User was renamed to Foundry User.
  foundry_user_role_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/53ca6127-db72-4b80-b1b0-d745d6d5456d"
}

resource "azurerm_resource_group" "demo" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_cognitive_account" "foundry" {
  name                          = "ai-${local.name}"
  resource_group_name           = azurerm_resource_group.demo.name
  location                      = azurerm_resource_group.demo.location
  kind                          = "AIServices"
  sku_name                      = "S0"
  custom_subdomain_name         = "ai-${local.name}"
  project_management_enabled    = true
  local_auth_enabled            = false
  public_network_access_enabled = true
  tags                          = local.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_cognitive_account_project" "demo" {
  name                 = "proj-${local.name}"
  cognitive_account_id = azurerm_cognitive_account.foundry.id
  location             = azurerm_resource_group.demo.location
  display_name         = "MCP Apps demo"
  description          = "Model access for the local MCP Apps and AG-UI sample."
  tags                 = local.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_cognitive_deployment" "model" {
  name                 = "model-${local.name}"
  cognitive_account_id = azurerm_cognitive_account.foundry.id

  model {
    format  = "OpenAI"
    name    = var.model_name
    version = var.model_version
  }

  sku {
    name     = var.model_sku
    capacity = var.model_capacity
  }
}

resource "azurerm_role_assignment" "developer" {
  scope              = azurerm_cognitive_account.foundry.id
  role_definition_id = local.foundry_user_role_id
  principal_id       = var.developer_object_id
  principal_type     = "User"
}

resource "azurerm_role_assignment" "project" {
  scope              = azurerm_cognitive_account.foundry.id
  role_definition_id = local.foundry_user_role_id
  principal_id       = azurerm_cognitive_account_project.demo.identity[0].principal_id
  principal_type     = "ServicePrincipal"
}
