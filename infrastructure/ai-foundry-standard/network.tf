resource "azurerm_virtual_network" "this" {
  name                = local.vnet_name
  address_space       = [local.vnet_cidr]
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
}

resource "azurerm_subnet" "private-endpoints" {
  name                 = "private-endpoints"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [local.pe_subnet_cidr]
}

resource "azurerm_subnet" "agents" {
  name                 = "agents"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [local.agent_subnet_cidr]
}

resource "azurerm_network_security_group" "this" {
  name                = local.nsg_name
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
}

resource "azurerm_subnet_network_security_group_association" "pe" {
  subnet_id                 = azurerm_subnet.private-endpoints.id
  network_security_group_id = azurerm_network_security_group.this.id
}

resource "azurerm_subnet_network_security_group_association" "agents" {
  subnet_id                 = azurerm_subnet.agents.id
  network_security_group_id = azurerm_network_security_group.this.id
}
