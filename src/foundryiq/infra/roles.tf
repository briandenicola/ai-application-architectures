resource "azurerm_role_assignment" "search_blob_reader" {
  scope                = azurerm_storage_account.this.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_search_service.this.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "search_model_user" {
  scope                = azapi_resource.foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_search_service.this.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "project_search_reader" {
  scope                = azurerm_search_service.this.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azapi_resource.project.output.identity.principalId
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "operator_blob_contributor" {
  scope                = azapi_resource.container.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.operator_object_id
}

resource "azurerm_role_assignment" "operator_search" {
  for_each = toset(["Search Service Contributor", "Search Index Data Contributor"])

  scope                = azurerm_search_service.this.id
  role_definition_name = each.value
  principal_id         = var.operator_object_id
}

locals {
  foundry_operator_roles = toset([
    "53ca6127-db72-4b80-b1b0-d745d6d5456d",
    "eadc314b-1a2d-4efa-be10-5d325db5065e",
  ])
}

resource "azurerm_role_assignment" "operator_foundry" {
  for_each = local.foundry_operator_roles

  scope              = azapi_resource.foundry.id
  role_definition_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/${each.value}"
  principal_id       = var.operator_object_id
}

resource "azurerm_role_assignment" "setup_blob_contributor" {
  scope                = azapi_resource.container.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.setup.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "setup_search" {
  for_each = toset(["Search Service Contributor", "Search Index Data Contributor"])

  scope                = azurerm_search_service.this.id
  role_definition_name = each.value
  principal_id         = azurerm_user_assigned_identity.setup.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "setup_foundry" {
  for_each = local.foundry_operator_roles

  scope              = azapi_resource.foundry.id
  role_definition_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/${each.value}"
  principal_id       = azurerm_user_assigned_identity.setup.principal_id
  principal_type     = "ServicePrincipal"
}
