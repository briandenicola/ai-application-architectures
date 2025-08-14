locals {
  location             = var.region
  resource_name        = "${random_pet.this.id}-${random_id.this.dec}"
  openai_name          = "${local.resource_name}-openai"
  ai_services_name     = "${local.resource_name}-foundry"
  search_service_name  = "${local.resource_name}-search"
  project_name         = "${local.resource_name}-aiproject"
  capability_host_name = "${local.resource_name}-caphost"
  appinsights_name     = "${local.resource_name}-appinsights"
  cosmosdb_name        = "${local.resource_name}-db"
  bing_name            = "${local.resource_name}-bing-grounding"
  vnet_name            = "${local.resource_name}-network"
  storage_account_name = "${replace(local.resource_name, "-", "")}sa"
  loganalytics_name    = "${local.resource_name}-logs"
  nsg_name             = "${local.resource_name}-nsg"
  vnet_cidr            = "192.168.0.0/16"
  pe_subnet_cidr       = cidrsubnet(local.vnet_cidr, 4, 1)
  agent_subnet_cidr    = cidrsubnet(local.vnet_cidr, 4, 2)
  project_id_guid      = "${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 0, 8)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 8, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 12, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 16, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 20, 12)}"
}
