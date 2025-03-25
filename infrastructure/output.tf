output "APP_NAME" {
    value = local.resource_name
    sensitive = false
}

output "APP_RESOURCE_GROUP" {
    value = azurerm_resource_group.this.name
    sensitive = false
}

output "OPENAI_ENDPOINT" {
    value = data.azurerm_cognitive_account.global.endpoint
    sensitive = false
}

output "OPENAI_KEY" {
    value = data.azurerm_cognitive_account.global.primary_access_key
    sensitive = true
}

output "OPENAI_EMBEDDING_ENDPOINT" {
    value = azurerm_cognitive_account.embedding.endpoint
    sensitive = false
}

output "OPENAI_EMBEDDING_KEY" {
    value = azurerm_cognitive_account.embedding.primary_access_key
    sensitive = true
}

output "OPENAI_VISION_ENDPOINT" {
    value = azurerm_cognitive_account.regional.endpoint
    sensitive = false
}

output "OPENAI_VISION_KEY" {
    value = azurerm_cognitive_account.regional.primary_access_key
    sensitive = true
}