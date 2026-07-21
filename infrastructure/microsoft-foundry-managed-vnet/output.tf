output "APP_NAME" {
    value = local.resource_name
    sensitive = false
}

output "APP_RESOURCE_GROUP" {
    value = azurerm_resource_group.this.name
    sensitive = false
}

# output "PROJECT_ENDPOINT" {
#     value = module.project_1.PROJECT_ENDPOINT
#     sensitive = false
# }