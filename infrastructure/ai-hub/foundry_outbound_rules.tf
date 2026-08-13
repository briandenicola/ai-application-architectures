
resource "azapi_resource" "approved_fqdn_rule" {
  for_each  = toset(var.approved_outbound_fqdns)
  type      = "Microsoft.MachineLearningServices/workspaces/outboundRules@2024-10-01"
  name      = "fqdn-${replace(replace(each.value, ".", "-"), "*", "wildcard")}"
  parent_id = azurerm_ai_foundry.this.id

  body = {
    properties = {
      type        = "FQDN"
      category    = "UserDefined"
      destination = each.value
    }
  }
}
