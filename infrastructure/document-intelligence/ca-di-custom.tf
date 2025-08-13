resource "azurerm_container_app" "cognitive_service_custom" {
  name                         = "cognitive-service-custom"
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
    external_enabled           = true
    target_port                = 5001
    transport                  = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }

    ip_security_restriction {
      name = "AllowHome"
      action = "Allow"
      ip_address_range = local.home_network
    } 
  }

  template {
    min_replicas = 1
    volume {
      name         = "cognitive-service-shared"
      storage_type = "EmptyDir"
    }
    volume {
      name         = "cognitive-service-logs"
      storage_type = "EmptyDir"
    }    
    container {
      name   = "custom-template"
      image  = "mcr.microsoft.com/azure-cognitive-services/form-recognizer/custom-template-3.0:2022-08-31"
      cpu    = 8
      memory = "16Gi"

      env {
        name  = "AzureCognitiveServiceLayoutHost"
        value = "https://${azurerm_container_app.cognitive_service_layout.ingress[0].fqdn}/"
      }
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
      env {
        name  = "Logging__Console__LogLevel__Default"
        value = "Information"
      }
      env {
        name  = "SharedRootFolder"
        value = "/shared"
      }
      env {
        name  = "Mounts__Shared"
        value = "/shared"
      }
      env {
        name  = "Mounts__Output"
        value = "/logs"
      }                        
      volume_mounts {
        name = "cognitive-service-shared"
        path = "/shared"
      }
      volume_mounts {
        name = "cognitive-service-logs"
        path = "/logs"
      }      
    }
    container {
      name   = "form-recognizer-studio"
      image  = "mcr.microsoft.com/azure-cognitive-services/form-recognizer/studio:3.0"
      cpu    = 8
      memory = "16Gi"

      env {
        name  = "ONPREM_LOCALFILE_BASEPATH"
        value = "/shared"
      }
      env {
        name  = "STORAGE_DATABASE_CONNECTION_STRING"
        value = "/shared/db/Application.db"
      }
      volume_mounts {
        name = "cognitive-service-shared"
        path = "/shared"
      }
      volume_mounts {
        name = "cognitive-service-shared"
        path = "/shared/db"
      }      
    }        
  }
}
