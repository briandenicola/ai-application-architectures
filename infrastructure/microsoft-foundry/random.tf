resource "random_uuid" "guid" {}

resource "random_id" "this" {
  byte_length = 2
}

resource "random_pet" "this" {
  length    = 1
  separator = ""
}

resource "random_password" "password" {
  length  = 25
  special = true
}
resource "random_integer" "vnet_cidr" {
  min = 10
  max = 250
}