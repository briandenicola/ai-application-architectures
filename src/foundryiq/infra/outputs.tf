output "demo" {
  description = "Non-secret connection details consumed by demo.py and the Copilot Studio walkthrough."
  value = {
    subscription_id      = var.subscription_id
    resource_group       = azurerm_resource_group.this.name
    location             = var.location
    storage_account      = azurerm_storage_account.this.name
    storage_resource_id  = azurerm_storage_account.this.id
    container_name       = azapi_resource.container.name
    search_endpoint      = "https://${azurerm_search_service.this.name}.search.windows.net"
    project_resource_id  = azapi_resource.project.id
    project_endpoint     = "https://${local.account_name}.services.ai.azure.com/api/projects/${local.project_name}"
    openai_endpoint      = "https://${local.account_name}.openai.azure.com"
    chat_deployment      = azapi_resource.model["chat"].name
    chat_model           = var.chat_model_name
    embedding_deployment = azapi_resource.model["embedding"].name
    embedding_model      = var.embedding_model_name
    knowledge_source     = "employee-handbook-blob"
    knowledge_base       = "employee-handbook"
    connection_name      = "employee-handbook-mcp"
    agent_name           = "employee-handbook-agent"
  }
}
