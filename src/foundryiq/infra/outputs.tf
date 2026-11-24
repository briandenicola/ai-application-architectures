output "demo" {
  description = "Non-secret connection details consumed by demo.py and the Copilot Studio walkthrough."
  value = {
    subscription_id             = var.subscription_id
    resource_group              = azurerm_resource_group.this.name
    location                    = var.location
    storage_account             = azurerm_storage_account.this.name
    storage_resource_id         = azurerm_storage_account.this.id
    container_name              = azapi_resource.container.name
    search_endpoint             = "https://${azurerm_search_service.this.name}.search.windows.net"
    project_resource_id         = azapi_resource.project.id
    project_endpoint            = "https://${local.ai_services_name}.services.ai.azure.com/api/projects/${local.project_name}"
    openai_endpoint             = "https://${local.ai_services_name}.openai.azure.com"
    chat_deployment             = azapi_resource.chat_model.name
    chat_model                  = var.chat_model_name
    embedding_deployment        = azapi_resource.embedding_model.name
    embedding_model             = var.embedding_model_name
    knowledge_source            = "employee-handbook-index-source"
    search_index                = "employee-handbook-index"
    knowledge_base              = "employee-handbook"
    connection_name             = "employee-handbook-mcp"
    agent_name                  = "employee-handbook-agent"
    operator_object_id          = var.operator_object_id
    application_insights_id     = azurerm_application_insights.this.id
    application_insights_app_id = azurerm_application_insights.this.app_id
    telemetry_connection_name   = "employee-handbook-insights"
    storage_private_ip          = azurerm_private_endpoint.blob.private_service_connection[0].private_ip_address
    setup_runner_id             = azurerm_container_app_job.setup.id
    setup_runner_name           = azurerm_container_app_job.setup.name
    setup_runner_image          = var.setup_runner_image
    setup_runner_client_id      = azurerm_user_assigned_identity.setup.client_id
  }
}
