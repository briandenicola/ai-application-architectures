output "APP_NAME" {
    value = local.resource_name
    sensitive = false
}

output "APP_RESOURCE_GROUP" {
    value = azurerm_resource_group.this.name
    sensitive = false
}

output "OPENAI_ENDPOINT" {
    value = azurerm_cognitive_account.this.endpoint
    sensitive = false
}

output "OPENAI_KEY" {
    value = azurerm_cognitive_account.this.primary_access_key
    sensitive = true
}

output "OPENAI_MODEL_ID" {
    value = azurerm_cognitive_deployment.gpt.model[0].name
    sensitive = false
}