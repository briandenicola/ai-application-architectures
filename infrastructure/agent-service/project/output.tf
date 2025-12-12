output "PROJECT_NAME" {
    value = var.foundry_project.name
    sensitive = false
}

output "PROJECT_RESOURCE_GROUP" {
    value = azurerm_resource_group.this.name
    sensitive = false
}

output "PROJECT_RESOURCE_GROUP_ID" {
    value = azurerm_resource_group.this.id
    sensitive = false
}

output "PROJECT_ENDPOINT" {
    value = "https://${var.foundry_project.ai_foundry.name}.services.ai.azure.com/api/projects/${var.foundry_project.name}"
    sensitive = false
}