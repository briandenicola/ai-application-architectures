resource "random_uuid" "guid" {}

locals {
  app_insights_name    = "${var.foundry_project.name}-appinsights"
}
