variable "subscription_id" {
  description = "Azure subscription ID; the Task targets resolve the active Azure CLI subscription."
  type        = string
}

variable "developer_object_id" {
  description = "Object ID of the signed-in Azure CLI user who runs the local agent; resolved by Task independently of Terraform provider authentication."
  type        = string
}

variable "location" {
  description = "Azure region for the Foundry account and project."
  type        = string
  default     = "eastus2"
}

variable "model_name" {
  description = "OpenAI model to deploy. Its resource name is generated automatically."
  type        = string
  default     = "gpt-5.5"
}

variable "model_version" {
  description = "Model version, or null to use Azure's current default version."
  type        = string
  default     = null
}

variable "model_sku" {
  description = "Model deployment SKU."
  type        = string
  default     = "GlobalStandard"

  validation {
    condition     = contains(["GlobalStandard", "DataZoneStandard", "Standard"], var.model_sku)
    error_message = "Use GlobalStandard, DataZoneStandard, or Standard."
  }
}

variable "model_capacity" {
  description = "Deployment capacity in thousands of tokens per minute for GPT-4.1."
  type        = number
  default     = 10

  validation {
    condition     = var.model_capacity >= 1 && floor(var.model_capacity) == var.model_capacity
    error_message = "Model capacity must be a positive integer."
  }
}
