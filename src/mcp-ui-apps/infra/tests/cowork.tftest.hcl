mock_provider "azurerm" {}
mock_provider "azapi" {}
mock_provider "random" {}

variables {
  subscription_id     = "00000000-0000-4000-8000-000000000001"
  developer_object_id = "00000000-0000-4000-8000-000000000002"
  function_image      = "crdemo.azurecr.io/banking-functions@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}

run "foundation_without_placeholder_apps" {
  command = plan

  variables {
    function_image = null
  }

  assert {
    condition     = length(azapi_resource.functions) == 0
    error_message = "The foundation must not deploy placeholder or unbuilt images."
  }
}

run "native_functions_with_private_storage" {
  command = plan

  assert {
    condition = (
      length(azapi_resource.functions) == 2 &&
      alltrue([for app in azapi_resource.functions : app.body.kind == "functionapp"]) &&
      alltrue([for app in azapi_resource.functions : app.body.properties.template.containers[0].image == var.function_image]) &&
      alltrue([for app in azapi_resource.functions : app.body.properties.configuration.activeRevisionsMode == "Single"])
    )
    error_message = "Both apps must run native Functions from the same immutable image, without concurrent host-storage revisions."
  }

  assert {
    condition = (
      azapi_resource.functions["gateway"].body.properties.configuration.ingress.external &&
      !azapi_resource.functions["banking"].body.properties.configuration.ingress.external &&
      alltrue([for app in azapi_resource.functions : !app.body.properties.configuration.ingress.allowInsecure])
    )
    error_message = "Only the gateway may have external ingress; neither app may accept insecure ingress."
  }

  assert {
    condition = (
      alltrue([for storage in azurerm_storage_account.functions : storage.public_network_access == "Disabled" && !storage.shared_access_key_enabled]) &&
      length(azurerm_private_endpoint.storage) == 6 &&
      length(azurerm_private_dns_zone_virtual_network_link.storage) == 3 &&
      alltrue([for endpoint in azurerm_private_endpoint.storage : !endpoint.private_service_connection[0].is_manual_connection])
    )
    error_message = "Both keyless host accounts need automatically approved Blob/Queue/Table private endpoints and linked private DNS."
  }

  assert {
    condition = (
      !azurerm_container_registry.functions.admin_enabled &&
      alltrue([for role in azurerm_role_assignment.image_pull : role.role_definition_name == "AcrPull"]) &&
      alltrue([for app in azapi_resource.functions : app.identity[0].type == "UserAssigned"]) &&
      alltrue([for app in azapi_resource.functions :
        contains([for setting in app.body.properties.template.containers[0].env : setting.name], "AzureWebJobsStorage__clientId") &&
        !contains([for setting in app.body.properties.template.containers[0].env : setting.name], "AzureWebJobsStorage")
      ])
    )
    error_message = "Image pulls and host storage must use managed identity, not registry passwords or storage connection strings."
  }
}

run "reject_mutable_image_tags" {
  command = plan

  variables {
    function_image = "crdemo.azurecr.io/banking-functions:latest"
  }

  expect_failures = [var.function_image]
}
