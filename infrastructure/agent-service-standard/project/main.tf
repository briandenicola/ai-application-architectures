locals {
  search_service_name  = "${var.foundry_project.name}-search"
  appinsights_name     = "${var.foundry_project.name}-appinsights"
  cosmosdb_name        = "${var.foundry_project.name}-db"
  capability_host_name = "${var.foundry_project.name}-hosting"
  storage_account_name = "${replace(var.foundry_project.name, "-", "")}sa" #change to guid base name
  project_id_guid      = "${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 0, 8)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 8, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 12, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 16, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 20, 12)}"
}
