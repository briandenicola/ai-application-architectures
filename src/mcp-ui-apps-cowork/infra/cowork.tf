data "azurerm_client_config" "current" {}

resource "random_uuid" "gateway_scope" {}
resource "random_uuid" "banking_role" {}
resource "random_uuid" "plugin" {}

locals {
  project_endpoint = "https://${azurerm_cognitive_account.foundry.custom_subdomain_name}.services.ai.azure.com/api/projects/${azurerm_cognitive_account_project.demo.name}"
  investigator     = "wire-investigator-${local.name}"
}

resource "azuread_application" "gateway" {
  display_name     = "banking-gateway-${local.name}"
  sign_in_audience = "AzureADMyOrg"
  owners           = [var.developer_object_id]
  api {
    requested_access_token_version = 2
    oauth2_permission_scope {
      id                         = random_uuid.gateway_scope.result
      value                      = "access_as_user"
      type                       = "User"
      enabled                    = true
      admin_consent_display_name = "Review synthetic banking wires"
      admin_consent_description  = "Read demo wires, investigate risk, and submit pending hold requests."
      user_consent_display_name  = "Review synthetic banking wires"
      user_consent_description   = "Use the synthetic banking demo on your behalf."
    }
  }
  lifecycle {
    ignore_changes = [identifier_uris]
  }
}

resource "azuread_application_identifier_uri" "gateway" {
  application_id = azuread_application.gateway.id
  identifier_uri = "api://${azuread_application.gateway.client_id}"
}

resource "azuread_application_pre_authorized" "azure_cli" {
  application_id       = azuread_application.gateway.id
  authorized_client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
  permission_ids       = [random_uuid.gateway_scope.result]
}

resource "azuread_service_principal" "gateway" {
  client_id = azuread_application.gateway.client_id
}

resource "azuread_application" "cowork" {
  display_name     = "banking-cowork-${local.name}"
  sign_in_audience = "AzureADMyOrg"
  owners           = [var.developer_object_id]
  single_page_application {
    redirect_uris = ["https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect"]
  }
  required_resource_access {
    resource_app_id = azuread_application.gateway.client_id
    resource_access {
      id   = random_uuid.gateway_scope.result
      type = "Scope"
    }
  }
}

resource "azuread_service_principal" "cowork" {
  client_id = azuread_application.cowork.client_id
}

resource "azuread_service_principal_delegated_permission_grant" "cowork" {
  service_principal_object_id          = azuread_service_principal.cowork.object_id
  resource_service_principal_object_id = azuread_service_principal.gateway.object_id
  claim_values                         = ["access_as_user"]
}

resource "azuread_application" "banking" {
  display_name     = "banking-tools-${local.name}"
  sign_in_audience = "AzureADMyOrg"
  owners           = [var.developer_object_id]
  api {
    requested_access_token_version = 2
  }
  app_role {
    id                   = random_uuid.banking_role.result
    allowed_member_types = ["Application"]
    description          = "Invoke banking tools from the gateway managed identity."
    display_name         = "Invoke banking tools"
    enabled              = true
    value                = "Banking.Invoke"
  }
  lifecycle {
    ignore_changes = [identifier_uris]
  }
}

resource "azuread_application_identifier_uri" "banking" {
  application_id = azuread_application.banking.id
  identifier_uri = "api://${azuread_application.banking.client_id}"
}

resource "azuread_service_principal" "banking" {
  client_id                    = azuread_application.banking.client_id
  app_role_assignment_required = true
}

resource "azurerm_user_assigned_identity" "function" {
  for_each            = toset(["gateway", "banking"])
  name                = "id-${each.key}-${local.name}"
  resource_group_name = azurerm_resource_group.demo.name
  location            = azurerm_resource_group.demo.location
  tags                = local.tags
}

resource "azuread_app_role_assignment" "gateway_banking" {
  app_role_id         = random_uuid.banking_role.result
  principal_object_id = azurerm_user_assigned_identity.function["gateway"].principal_id
  resource_object_id  = azuread_service_principal.banking.object_id
}

resource "azurerm_storage_account" "functions" {
  for_each                        = toset(["gateway", "banking"])
  name                            = "st${substr(sha256("${local.name}-${each.key}"), 0, 20)}"
  resource_group_name             = azurerm_resource_group.demo.name
  location                        = azurerm_resource_group.demo.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"
  tags                            = local.tags
}

resource "azurerm_storage_container" "deployment" {
  for_each              = toset(["gateway", "banking"])
  name                  = "deploy-${each.key}"
  storage_account_id    = azurerm_storage_account.functions[each.key].id
  container_access_type = "private"
}

resource "azurerm_storage_container" "holds" {
  name                  = "hold-requests"
  storage_account_id    = azurerm_storage_account.functions["banking"].id
  container_access_type = "private"
}

resource "azurerm_role_assignment" "function_storage" {
  for_each             = azurerm_user_assigned_identity.function
  scope                = azurerm_storage_account.functions[each.key].id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = each.value.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "gateway_foundry" {
  scope              = azurerm_cognitive_account_project.demo.id
  role_definition_id = local.foundry_user_role_id
  principal_id       = azurerm_user_assigned_identity.function["gateway"].principal_id
  principal_type     = "ServicePrincipal"
}

resource "azurerm_service_plan" "functions" {
  for_each            = toset(["gateway", "banking"])
  name                = "plan-${each.key}-${local.name}"
  resource_group_name = azurerm_resource_group.demo.name
  location            = azurerm_resource_group.demo.location
  os_type             = "Linux"
  sku_name            = "FC1"
  tags                = local.tags
}

locals {
  function_storage_settings = {
    for role, storage in azurerm_storage_account.functions : role => {
      ENTRA_TENANT_ID                      = data.azurerm_client_config.current.tenant_id
      AzureWebJobsStorage__credential      = "managedidentity"
      AzureWebJobsStorage__blobServiceUri  = storage.primary_blob_endpoint
      AzureWebJobsStorage__queueServiceUri = storage.primary_queue_endpoint
      AzureWebJobsStorage__tableServiceUri = storage.primary_table_endpoint
    }
  }
}

resource "azurerm_function_app_flex_consumption" "banking" {
  name                                           = "func-banking-${local.name}"
  resource_group_name                            = azurerm_resource_group.demo.name
  location                                       = azurerm_resource_group.demo.location
  service_plan_id                                = azurerm_service_plan.functions["banking"].id
  storage_container_type                         = "blobContainer"
  storage_container_endpoint                     = "${azurerm_storage_account.functions["banking"].primary_blob_endpoint}${azurerm_storage_container.deployment["banking"].name}"
  storage_authentication_type                    = "UserAssignedIdentity"
  storage_user_assigned_identity_id              = azurerm_user_assigned_identity.function["banking"].id
  runtime_name                                   = "node"
  runtime_version                                = "22"
  maximum_instance_count                         = 5
  instance_memory_in_mb                          = 2048
  https_only                                     = true
  webdeploy_publish_basic_authentication_enabled = false
  tags                                           = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.function["banking"].id]
  }

  app_settings = merge(local.function_storage_settings["banking"], {
    APP_ROLE                      = "banking"
    AZURE_CLIENT_ID               = azurerm_user_assigned_identity.function["banking"].client_id
    AzureWebJobsStorage__clientId = azurerm_user_assigned_identity.function["banking"].client_id
    ENTRA_AUDIENCE                = azuread_application.banking.client_id
    GATEWAY_CLIENT_ID             = azurerm_user_assigned_identity.function["gateway"].client_id
    HOLDS_BLOB_URL                = azurerm_storage_account.functions["banking"].primary_blob_endpoint
  })

  site_config {
    minimum_tls_version = "1.2"
  }

  depends_on = [azurerm_role_assignment.function_storage, azuread_app_role_assignment.gateway_banking]
}

resource "azurerm_function_app_flex_consumption" "gateway" {
  name                                           = "func-gateway-${local.name}"
  resource_group_name                            = azurerm_resource_group.demo.name
  location                                       = azurerm_resource_group.demo.location
  service_plan_id                                = azurerm_service_plan.functions["gateway"].id
  storage_container_type                         = "blobContainer"
  storage_container_endpoint                     = "${azurerm_storage_account.functions["gateway"].primary_blob_endpoint}${azurerm_storage_container.deployment["gateway"].name}"
  storage_authentication_type                    = "UserAssignedIdentity"
  storage_user_assigned_identity_id              = azurerm_user_assigned_identity.function["gateway"].id
  runtime_name                                   = "node"
  runtime_version                                = "22"
  maximum_instance_count                         = 5
  instance_memory_in_mb                          = 2048
  https_only                                     = true
  webdeploy_publish_basic_authentication_enabled = false
  tags                                           = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.function["gateway"].id]
  }
  app_settings = merge(local.function_storage_settings["gateway"], {
    APP_ROLE                      = "gateway"
    AZURE_CLIENT_ID               = azurerm_user_assigned_identity.function["gateway"].client_id
    AzureWebJobsStorage__clientId = azurerm_user_assigned_identity.function["gateway"].client_id
    ENTRA_AUDIENCE                = azuread_application.gateway.client_id
    BANKING_URL                   = "https://${azurerm_function_app_flex_consumption.banking.default_hostname}"
    BANKING_AUDIENCE              = azuread_application_identifier_uri.banking.identifier_uri
    FOUNDRY_PROJECT_ENDPOINT      = local.project_endpoint
    FOUNDRY_AGENT_NAME            = local.investigator
  })
  site_config {
    minimum_tls_version = "1.2"
  }
  depends_on = [azurerm_role_assignment.function_storage, azurerm_role_assignment.gateway_foundry]
}
