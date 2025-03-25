variable "region" {
  description = "Region to deploy resources to"
  default     =  "eastus2"
}

variable "tags" {
  description = "Tags to apply to Resource Group"
}

variable "deploy_ai_workspace" {
  description = "Deploy azurerm_machine_learning_workspace"
  default = "false"
}
