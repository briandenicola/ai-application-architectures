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
