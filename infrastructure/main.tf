

locals {
  location                        = var.region
  embedding_location              = "canadaeast"
  regional_location               = "westus"
  resource_name                   = "${random_pet.this.id}-${random_id.this.dec}"
  openai_name                     = "${local.resource_name}-openai"
  hub_name                        = "${local.resource_name}-aihub"
  project_name                    = "${local.resource_name}-aiproject"
  kv_name                         = "${local.resource_name}-kv"
  acr_name                        = "${replace(local.resource_name, "-", "")}acr"
  storage_account_name            = "${replace(local.resource_name, "-", "")}sa"
  appinsights_name                = "${local.resource_name}-appinsights"
  loganalytics_name               = "${local.resource_name}-logs"
  machine_learning_workspace_name = "${local.resource_name}-ml"
}