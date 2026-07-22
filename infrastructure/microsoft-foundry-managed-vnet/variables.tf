variable "region" {
  description = "Region to deploy resources to"
  default     = "eastus2"
}

variable "tags" {
  description = "Tags to apply to Resource Group"
}

variable "enable_dns" {
  description = "Enable Private DNS Zones and VNet links"
  type        = bool
  default     = true
}

variable "managed_network_isolation_mode" {
  description = "Managed VNet isolation mode for the Foundry account. Use AllowOnlyApprovedOutbound when outbound FQDN rules should be enforced."
  type        = string
  default     = "AllowOnlyApprovedOutbound"

  validation {
    condition     = contains(["AllowInternetOutbound", "AllowOnlyApprovedOutbound"], var.managed_network_isolation_mode)
    error_message = "managed_network_isolation_mode must be either AllowInternetOutbound or AllowOnlyApprovedOutbound."
  }
}

variable "managed_network_fqdn_outbound_rules" {
  description = "FQDN outbound rules for the Foundry managed VNet. This accepts the Azure Machine Learning-style rule shape and emits the Foundry AzAPI FQDN rule shape."
  type = map(object({
    type = string
    destination = object({
      fqdn = string
    })
    status = string
  }))
  default = {
    fqdn-msryechoacr = {
      type = "FQDN"
      destination = {
        fqdn = "msryechoacr.azurecr.io"
      }
      status = "Active"
    }
    fqdn-anacondaorg = {
      type = "FQDN"
      destination = {
        fqdn = "*.anaconda.org"
      }
      status = "Active"
    }
    fqdn-anacondacom = {
      type = "FQDN"
      destination = {
        fqdn = "*.anaconda.com"
      }
      status = "Active"
    }
    fqdn-anaconda = {
      type = "FQDN"
      destination = {
        fqdn = "anaconda.com"
      }
      status = "Active"
    }
    fqdn-pypi = {
      type = "FQDN"
      destination = {
        fqdn = "pypi.org"
      }
      status = "Active"
    }
    fqdn-pythonhosted = {
      type = "FQDN"
      destination = {
        fqdn = "*.pythonhosted.org"
      }
      status = "Active"
    }
    fqdn-pytorchorg = {
      type = "FQDN"
      destination = {
        fqdn = "*.pytorch.org"
      }
      status = "Active"
    }
    fqdn-pytorch = {
      type = "FQDN"
      destination = {
        fqdn = "pytorch.org"
      }
      status = "Active"
    }
    fqdn-msryechoacr-southcentralus = {
      type = "FQDN"
      destination = {
        fqdn = "msryechoacr.southcentralus.data.azurecr.io"
      }
      status = "Active"
    }
    fqdn-msryechoacr-eastus = {
      type = "FQDN"
      destination = {
        fqdn = "msryechoacr.eastus.data.azurecr.io"
      }
      status = "Active"
    }
  }

  validation {
    condition     = alltrue([for rule in var.managed_network_fqdn_outbound_rules : rule.type == "FQDN"])
    error_message = "All managed_network_fqdn_outbound_rules entries must have type = \"FQDN\"."
  }
}
