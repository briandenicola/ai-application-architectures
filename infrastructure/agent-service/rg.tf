resource "azurerm_resource_group" "this" {
  name     = "${local.resource_name}-ai_rg"
  location = local.location
  tags = {
    Application = var.tags
    DeployedOn  = timestamp()
    AppName     = local.resource_name
    Tier        = "AI Foundry; Bing Grounding"
  }
}

resource "azurerm_resource_group" "logs" {
  name     = "${local.resource_name}-logs_rg"
  location = local.location
  tags = {
    Application = var.tags
    DeployedOn  = timestamp()
    AppName     = local.resource_name
    Tier        = "Azure Monitor; Azure Log Analytics"
  }
}

resource "azurerm_resource_group" "core" {
  name     = "${local.resource_name}-vnet_rg"
  location = local.location
  tags = {
    Application = var.tags
    DeployedOn  = timestamp()
    AppName     = local.resource_name
    Tier        = "Azure Virtual Network; Azure Private Endpoints; Azure Network Security Group"
  }
}