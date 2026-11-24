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
  default     = "eastus2"
}

variable "search_sku" {
  type        = string
  description = "Basic or Standard; Free does not support this managed-identity demo."
  default     = "basic"

  validation {
    condition     = contains(["basic", "standard"], var.search_sku)
    error_message = "Use basic or standard."
  }
}

variable "chat_model_name" {
  type        = string
  description = "Model used for the agent and knowledge-base query planning."
  default     = "gpt-5-mini"
}

variable "chat_model_version" {
  type        = string
  description = "Explicit model version."
  default     = "2025-08-07"
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
  default     = "Standard"
}

variable "embedding_model_capacity" {
  type        = number
  description = "Embedding deployment capacity units."
  default     = 10
}
