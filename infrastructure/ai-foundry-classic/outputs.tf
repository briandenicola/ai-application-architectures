output "OPENAI_RESOURCE_ID" {
  value     = azurerm_cognitive_account.this.id
  sensitive = false
}

output "OPENAI_ENDPOINT" {
  value     = azurerm_cognitive_account.this.endpoint
  sensitive = false
}

output "OPENAI_RESOURCE_NAME" {
  value     = azurerm_cognitive_account.this.name
  sensitive = false
}
