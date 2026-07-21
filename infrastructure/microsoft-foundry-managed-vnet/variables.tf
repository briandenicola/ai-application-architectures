variable "region" {
  description = "Region to deploy resources to"
  default     =  "eastus2"
}

variable "tags" {
  description = "Tags to apply to Resource Group"
}

variable "enable_dns" {
  description = "Enable Private DNS Zones and VNet links"
  type        = bool
  default     = true
}