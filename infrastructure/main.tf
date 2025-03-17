resource "random_id" "this" {
  byte_length = 2
}

resource "random_pet" "this" {
  length    = 1
  separator = ""
}

resource "random_password" "password" {
  length  = 25
  special = true
}

locals {
  location                        = var.region
  embedding_location              = "canadaeast"
  global_location                 = "eastus2"
  resource_name                   = "${random_pet.this.id}-${random_id.this.dec}"
  openai_name                     = "${local.resource_name}-openai"
  kv_name                         = "${local.resource_name}-kv"
  acr_name                        = "${replace(local.resource_name, "-", "")}acr"
  storage_account_name            = "${replace(local.resource_name, "-", "")}sa"
  appinsights_name                = "${local.resource_name}-appinsights"
  loganalytics_name               = "${local.resource_name}-logs"
  machine_learning_workspace_name = "${local.resource_name}-ml"
}

resource "azurerm_resource_group" "this" {
  name     = "${local.resource_name}_rg"
  location = local.location

  tags = {
    Application = var.tags
    Components  = ""
    DeployedOn  = timestamp()
    Deployer    = data.azurerm_client_config.current.object_id
  }
}
