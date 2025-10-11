data "azurerm_client_config" "current" {}
data "azurerm_subscription" "current" {}

locals {
  location          = var.region
  resource_name     = "${random_pet.this.id}-${random_id.this.dec}"
  appinsights_name  = "${local.resource_name}-appinsights"
  loganalytics_name = "${local.resource_name}-logs"
  openai_name = "${local.resource_name}-openai"
}

