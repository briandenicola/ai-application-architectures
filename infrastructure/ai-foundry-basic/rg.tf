resource "azurerm_resource_group" "this" {
  name     = "${local.resource_name}-ai_rg"
  location = local.location
  tags = {
    Application = var.tags
    DeployedOn  = timestamp()
    AppName     = local.resource_name
    Tier        = "Azure OpenAI; Azure AI Foundry; "
  }
}

resource "azurerm_resource_group" "logs" {
  name     = "${local.resource_name}-logs_rg"
  location = local.location
  tags = {
    Application = var.tags
    DeployedOn  = timestamp()
    AppName     = local.resource_name
    Tier        = "Azure Monitor; Azure Log Analytics; Azure Application Insights"
  }
}

resource "azurerm_resource_group" "core" {
  name     = "${local.resource_name}-core_rg"
  location = local.location
  tags = {
    Application = var.tags
    DeployedOn  = timestamp()
    AppName     = local.resource_name
    Tier        = "Azure Key Vault; Azure Storage; Azure Container Registry"
  }
}

resource "azurerm_resource_group" "ml" {
  count    = var.deploy_ai_workspace == "true" ? 1 : 0
  name     = "${local.resource_name}-ml_rg"
  location = local.location
  tags = {
    Application = var.tags
    DeployedOn  = timestamp()
    AppName     = local.resource_name
    Tier        = "Azure Machine Learning Hub"
  }
}
