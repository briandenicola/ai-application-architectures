data "azurerm_client_config" "current" {}

resource "random_uuid" "plugin" {}

locals {
  project_endpoint = "https://${azurerm_cognitive_account.foundry.custom_subdomain_name}.services.ai.azure.com/api/projects/${azurerm_cognitive_account_project.demo.name}"
  investigator     = "wire-investigator-${local.name}"
}

resource "azurerm_user_assigned_identity" "function" {
  for_each            = toset(["gateway", "banking"])
  name                = "id-${each.key}-${local.name}"
  resource_group_name = azurerm_resource_group.demo.name
  location            = azurerm_resource_group.demo.location
  tags                = local.tags
}

resource "azurerm_storage_account" "functions" {
  for_each                        = toset(["gateway", "banking"])
  name                            = "st${substr(sha256("${local.name}-${each.key}"), 0, 20)}"
  resource_group_name             = azurerm_resource_group.demo.name
  location                        = azurerm_resource_group.demo.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  shared_access_key_enabled       = false
  public_network_access           = "Disabled"
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"
  tags                            = local.tags
}

resource "azurerm_storage_container" "holds" {
  name                  = "hold-requests"
  storage_account_id    = azurerm_storage_account.functions["banking"].id
  container_access_type = "private"
}

resource "azurerm_role_assignment" "function_storage" {
  for_each             = azurerm_user_assigned_identity.function
  scope                = azurerm_storage_account.functions[each.key].id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = each.value.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "function_diagnostics" {
  for_each             = azurerm_user_assigned_identity.function
  scope                = azurerm_storage_account.functions[each.key].id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = each.value.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "gateway_foundry" {
  scope              = azurerm_cognitive_account_project.demo.id
  role_definition_id = local.foundry_user_role_id
  principal_id       = azurerm_user_assigned_identity.function["gateway"].principal_id
  principal_type     = "ServicePrincipal"
}

locals {
  function_storage_settings = {
    for role, storage in azurerm_storage_account.functions : role => {
      AzureWebJobsStorage__credential      = "managedidentity"
      AzureWebJobsStorage__blobServiceUri  = storage.primary_blob_endpoint
      AzureWebJobsStorage__queueServiceUri = storage.primary_queue_endpoint
      AzureWebJobsStorage__tableServiceUri = storage.primary_table_endpoint
    }
  }
}
