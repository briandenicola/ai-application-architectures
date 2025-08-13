resource "time_sleep" "wait_rbac" {
  depends_on = [
    azurerm_role_assignment.cosmosdb_operator_ai_foundry_project,
    azurerm_role_assignment.storage_blob_data_contributor_ai_foundry_project,
    azurerm_role_assignment.search_index_data_contributor_ai_foundry_project,
    azurerm_role_assignment.search_service_contributor_ai_foundry_project
  ]
  create_duration = "60s"
}

resource "time_sleep" "wait_project_identities" {
  depends_on = [
    azapi_resource.ai_foundry_project
  ]
  create_duration = "10s"
}