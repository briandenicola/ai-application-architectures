resource "azurerm_container_app" "cognitive_service_layout" {
  name                         = "cognitive-service-layout"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  workload_profile_name        = local.workload_profile_name

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aca_identity.id]
  }

  ingress {
    allow_insecure_connections = true
    external_enabled           = false
    target_port                = 5000
    transport                  = "http"
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }

  }

  template {
    min_replicas = 1
    container {
      name   = "cognitive-service-layout"
      image  = "mcr.microsoft.com/azure-cognitive-services/form-recognizer/layout-3.1:2023-07-31"
      cpu    = 8
      memory = "16Gi"

      env {
        name  = "EULA"
        value = "accept"
      }
      env {
        name  = "billing"
        value = azurerm_cognitive_account.this.endpoint
      }
      env {
        name  = "apikey"
        value = azurerm_cognitive_account.this.primary_access_key 
      }
   }
  }
}
