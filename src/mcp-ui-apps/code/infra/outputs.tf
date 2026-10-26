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
