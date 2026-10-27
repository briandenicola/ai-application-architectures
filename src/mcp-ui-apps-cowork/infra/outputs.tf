output "resource_group_name" {
  description = "Resource group containing the demo infrastructure."
  value       = azurerm_resource_group.demo.name
}

output "agent_environment" {
  description = "Non-secret configuration consumed by scripts/configure_foundry.py."
  value = {
    LLM_MODE                = "azure"
    AZURE_OPENAI_ENDPOINT   = "https://${azurerm_cognitive_account.foundry.custom_subdomain_name}.openai.azure.com"
    AZURE_OPENAI_DEPLOYMENT = azurerm_cognitive_deployment.model.name
  }
}

output "cowork" {
  description = "Non-secret deployment and Microsoft Cowork packaging settings."
  value = {
    subscription_id   = var.subscription_id
    resource_group    = azurerm_resource_group.demo.name
    tenant_id         = data.azurerm_client_config.current.tenant_id
    gateway_app       = azurerm_function_app_flex_consumption.gateway.name
    banking_app       = azurerm_function_app_flex_consumption.banking.name
    mcp_url           = "https://${azurerm_function_app_flex_consumption.gateway.default_hostname}/mcp"
    gateway_client_id = azuread_application.gateway.client_id
    oauth_client_id   = azuread_application.cowork.client_id
    oauth_scope       = "${azuread_application_identifier_uri.gateway.identifier_uri}/access_as_user"
    plugin_id         = random_uuid.plugin.result
    project_endpoint  = local.project_endpoint
    agent_name        = local.investigator
    model_deployment  = azurerm_cognitive_deployment.model.name
  }
}
