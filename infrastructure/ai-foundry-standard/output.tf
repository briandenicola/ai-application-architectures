output "APP_NAME" {
    value = local.resource_name
    sensitive = false
}

output "APP_RESOURCE_GROUP" {
    value = azurerm_resource_group.this.name
    sensitive = false
}

output "FOUNDRY_PROJECT_CONNECTION_STRING" {
    #<HostName>;<AzureSubscriptionId>;<ResourceGroup>;<ProjectName>
    value = "${trimsuffix(trimprefix(azapi_resource.ai_foundry.output.properties.discovery_url,"https://"), "/discovery")};${data.azurerm_subscription.current.subscription_id};${local.resource_name}-ai_rg;${local.project_name}" 
    sensitive = false
}