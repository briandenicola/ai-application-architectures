resource "random_id" "this" {
  byte_length = 2
}

resource "random_pet" "this" {
  length = 1
  separator  = ""
}

resource "random_password" "password" {
  length = 25
  special = true
}

locals {
    location                    = var.region
    resource_name               = "${random_pet.this.id}-${random_id.this.dec}"
}


resource "azurerm_resource_group" "this" {
  name                  = "${local.resource_name}_rg"
  location              = local.location
  
  tags     = {
    Application = var.tags
    Components  = ""
    DeployedOn  = timestamp()
    Deployer    = data.azurerm_client_config.current.principal_id
  }
}
