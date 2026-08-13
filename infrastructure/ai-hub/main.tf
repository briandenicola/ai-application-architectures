
locals {
  location             = var.region
  resource_name        = "${random_pet.this.id}-${random_id.this.dec}"
  hub_name             = "${local.resource_name}-aihub"
  project_name         = "${local.resource_name}-aiproject"
  kv_name              = "${local.resource_name}-kv"
  acr_name             = "${replace(local.resource_name, "-", "")}acr"
  storage_account_name = "${replace(local.resource_name, "-", "")}sa"
  appinsights_name     = "${local.resource_name}-appinsights"
  loganalytics_name    = "${local.resource_name}-logs"
  vnet_name            = "${local.resource_name}-network"
  nsg_name             = "${local.resource_name}-nsg"
  vnet_cidr            = "10.${random_integer.vnet_cidr.result}.0.0/16"
  pe_subnet_cidr       = cidrsubnet(local.vnet_cidr, 4, 1)
  agent_subnet_cidr    = cidrsubnet(local.vnet_cidr, 4, 2)
}
