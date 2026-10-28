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
    subscription_id  = var.subscription_id
    resource_group   = azurerm_resource_group.demo.name
    tenant_id        = data.azurerm_client_config.current.tenant_id
    gateway_app      = local.container_app_names.gateway
    banking_app      = local.container_app_names.banking
    registry_name    = azurerm_container_registry.functions.name
    registry_server  = azurerm_container_registry.functions.login_server
    mcp_url          = "https://${local.gateway_hostname}/mcp"
    plugin_id        = random_uuid.plugin.result
    project_endpoint = local.project_endpoint
    agent_name       = local.investigator
    model_deployment = azurerm_cognitive_deployment.model.name
  }
}
