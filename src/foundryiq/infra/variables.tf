variable "subscription_id" {
  type        = string
  description = "Subscription explicitly selected in .env."

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "Set AZURE_SUBSCRIPTION_ID to an Azure subscription GUID."
  }
}

variable "location" {
  type        = string
  description = "Region supporting Foundry, agentic retrieval, and the selected models."
  default     = "canadacentral"
}

variable "search_sku" {
  type        = string
  description = "Private managed Blob ingestion requires S2, S3, L1, or L2."
  default     = "standard2"

  validation {
    condition     = contains(["standard2", "standard3", "storage_optimized_l1", "storage_optimized_l2"], var.search_sku)
    error_message = "Use standard2 or another tier supporting managed private Blob ingestion."
  }
}

variable "operator_object_id" {
  type        = string
  description = "Azure CLI identity running Task, independently of Terraform's deployment credentials."

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.operator_object_id))
    error_message = "Use task up to derive the operator object ID from the selected Azure CLI identity."
  }
}

variable "network_address_space" {
  type        = string
  description = "IPv4 VNet CIDR supplied in .env; two /27 subnets are derived from it."

  validation {
    condition     = can(cidrnetmask(var.network_address_space)) && try(tonumber(split("/", var.network_address_space)[1]) <= 26, false)
    error_message = "Supply an IPv4 CIDR large enough for two /27 subnets (prefix length <= 26)."
  }
}

variable "setup_runner_image" {
  type        = string
  description = "Pinned official Azure CLI image with Python for the private setup job."
  default     = "mcr.microsoft.com/azure-cli:2.93.0-azurelinux3.0"
}

variable "chat_model_name" {
  type        = string
  description = "Model used for the agent and knowledge-base query planning."
  default     = "gpt-5.4-mini"
}

variable "chat_model_version" {
  type        = string
  description = "Explicit model version."
  default     = "2026-03-17"
}

variable "chat_model_sku" {
  type        = string
  description = "Deployment SKU for the chat model."
  default     = "GlobalStandard"
}

variable "chat_model_capacity" {
  type        = number
  description = "Chat deployment capacity units; quota depends on model and SKU."
  default     = 10
}

variable "embedding_model_name" {
  type        = string
  description = "Embedding model used by the managed Blob ingestion pipeline."
  default     = "text-embedding-3-small"
}

variable "embedding_model_version" {
  type        = string
  description = "Explicit embedding model version."
  default     = "1"
}

variable "embedding_model_sku" {
  type        = string
  description = "Deployment SKU for the embedding model."
  default     = "GlobalStandard"
}

variable "embedding_model_capacity" {
  type        = number
  description = "Embedding deployment capacity units."
  default     = 10
}
