variable "foundry_project" {
  type = object({
    name          = string
    resource_name = string
    location      = string
    ai_foundry_id = string
    tag           = string
    dns = ojbect({
      search_private_dns_zone_id  = string
      cosmos_private_dns_zone_id  = string
      storage_private_dns_zone_id = string
    })
    pe_subnet_id = string
    logs = object({
      workspace_id = string
    })
    models = list(object({
      name            = string
      version         = string
      format          = string
    }))
  })
}
