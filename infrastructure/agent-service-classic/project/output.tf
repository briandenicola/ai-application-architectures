output "PROJECT_NAME" {
    value = var.foundry_project.name
    sensitive = false
}

output "PROJECT_RESOURCE_GROUP" {
    value = azurerm_resource_group.this.name
    sensitive = false
}

output "PROJECT_ENDPOINT" {
    value = ""
    sensitive = false
}

output "PROJECT_GUID" {
    value = local.project_id_guid
    sensitive = true
}
