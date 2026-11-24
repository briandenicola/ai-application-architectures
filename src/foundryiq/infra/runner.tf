resource "azurerm_user_assigned_identity" "setup" {
  name                = "${local.resource_name}-setup-id"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  tags                = local.tags
}

resource "azurerm_container_app_environment" "setup" {
  name                               = "${local.resource_name}-runner-env"
  resource_group_name                = azurerm_resource_group.this.name
  location                           = azurerm_resource_group.this.location
  infrastructure_resource_group_name = "${local.resource_name}-runner_rg"
  infrastructure_subnet_id           = azurerm_subnet.runner.id
  logs_destination                   = ""
  tags                               = local.tags

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }

  depends_on = [
    azurerm_nat_gateway_public_ip_association.this,
    azurerm_subnet_nat_gateway_association.runner,
    azurerm_private_dns_zone_virtual_network_link.blob,
    azurerm_private_endpoint.blob,
  ]
}

resource "azurerm_container_app_job" "setup" {
  name                         = trimsuffix(substr("${local.resource_name}-setup", 0, 32), "-")
  resource_group_name          = azurerm_resource_group.this.name
  location                     = azurerm_resource_group.this.location
  container_app_environment_id = azurerm_container_app_environment.setup.id
  workload_profile_name        = "Consumption"
  replica_timeout_in_seconds   = 2100
  replica_retry_limit          = 0
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.setup.id]
  }

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name    = "setup"
      image   = var.setup_runner_image
      cpu     = 0.5
      memory  = "1Gi"
      command = ["python3", "-c"]
      args    = ["raise SystemExit('Start this job through task setup to supply the demo bundle.')"]
    }
  }

  depends_on = [
    azurerm_role_assignment.setup_blob_contributor,
    azurerm_role_assignment.setup_search,
    azurerm_role_assignment.setup_foundry,
    azurerm_role_assignment.setup_model_user,
  ]
}
