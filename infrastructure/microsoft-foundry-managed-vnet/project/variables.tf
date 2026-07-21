variable "foundry_project" {
  type = object({
    name          = string
    resource_name = string
    location      = string
    resource_group= object({
      name = string
      id   = string
    })
    ai_foundry    = object({
      name        = string
      id          = string
    }) 
    tag           = string
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
