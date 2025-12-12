locals {
  location                     = var.region
  resource_name                = "${random_pet.this.id}-${random_id.this.dec}"
  ai_services_name             = "${local.resource_name}-foundry"
  appinsights_name             = "${local.resource_name}-appinsights"
  bing_name                    = "${local.resource_name}-bing-grounding"
  vnet_name                    = "${local.resource_name}-network"
  loganalytics_name            = "${local.resource_name}-logs"
  nsg_name                     = "${local.resource_name}-nsg"
  foundry_storage_account_name = "${substr(replace(random_uuid.guid.result, "-", ""), 0, 22)}sa"
  vnet_cidr                    = "10.${random_integer.vnet_cidr.result}.0.0/16"
  pe_subnet_cidr               = cidrsubnet(local.vnet_cidr, 4, 1)
  agent_subnet_cidr            = cidrsubnet(local.vnet_cidr, 4, 2)

  # foreach is done in parallel and projects depend on ai_foundry parent resource.  For Demo purposes we are creating 2 projects statically.
  project_name = "${local.resource_name}-project"

}
