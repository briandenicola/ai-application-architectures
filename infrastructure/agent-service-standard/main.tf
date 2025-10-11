locals {
  location             = var.region
  resource_name        = "${random_pet.this.id}-${random_id.this.dec}"
  ai_services_name     = "${local.resource_name}-foundry"
  appinsights_name     = "${local.resource_name}-appinsights"
  bing_name            = "${local.resource_name}-bing-grounding"
  vnet_name            = "${local.resource_name}-network"
  loganalytics_name    = "${local.resource_name}-logs"
  nsg_name             = "${local.resource_name}-nsg"
  vnet_cidr            = "192.168.0.0/16"
  pe_subnet_cidr       = cidrsubnet(local.vnet_cidr, 4, 1)
  agent_subnet_cidr    = cidrsubnet(local.vnet_cidr, 4, 2)
  projects             = ["${local.resource_name}-projectA", "${local.resource_name}-projectB"]
}
