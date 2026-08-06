locals {
  location                     = var.region
  resource_name                = "${random_pet.this.id}-${random_id.this.dec}"
  ai_services_name             = "${local.resource_name}-foundry"
  appinsights_name             = "${local.resource_name}-appinsights"
  vnet_name                    = "${local.resource_name}-network"
  loganalytics_name            = "${local.resource_name}-logs"

  # for_each is done in parallel and projects depend on ai_foundry parent resource.  
  # For Demo purposes we are creating a project statically.
  project_name = "${local.resource_name}-project"

}
