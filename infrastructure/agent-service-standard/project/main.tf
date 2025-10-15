resource "random_uuid" "guid" {}

locals {
  project_rg_name      = "${var.foundry_project.name}_rg"
  search_service_name  = "${var.foundry_project.name}-search"
  app_insights_name    = "${var.foundry_project.name}-appinsights"
  cosmosdb_name        = "${var.foundry_project.name}-db"
  capability_host_name = "${var.foundry_project.name}-hosting"
  storage_account_name = "${substr(replace(random_uuid.guid.result, "-", ""), 0, 22)}sa"
  project_id_guid      = "${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 0, 8)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 8, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 12, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 16, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 20, 12)}"
}
