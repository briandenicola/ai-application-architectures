resource "azurerm_resource_group" "this" {
  name     = "${var.foundry_project.name}_rg"
  location = var.foundry_project.location
  tags = {
    Application = var.foundry_project.tag
    DeployedOn  = timestamp()
    AppName     = var.foundry_project.resource_name
    Tier        = "Azure AI Foundry Project; Azure Cosmos DB; Azure AI Search; Azure AI Foundry Capacity Host; Azure Storage;"
  }
}
