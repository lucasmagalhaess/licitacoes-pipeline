terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

# Resource Group — agrupa todos os recursos do projeto
resource "azurerm_resource_group" "licitacoes" {
  name     = var.resource_group_name
  location = var.location
}

# Storage Account — Data Lake bronze e silver
resource "azurerm_storage_account" "datalake" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.licitacoes.name
  location                 = azurerm_resource_group.licitacoes.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# Containers — camadas do Data Lake
resource "azurerm_storage_container" "bronze" {
  name                  = "bronze"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "silver" {
  name                  = "silver"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "gold" {
  name                  = "gold"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

# Azure SQL Server
resource "azurerm_mssql_server" "licitacoes" {
  name                         = var.sql_server_name
  resource_group_name          = azurerm_resource_group.licitacoes.name
  location                     = azurerm_resource_group.licitacoes.location
  version                      = "12.0"
  administrator_login          = var.sql_admin_login
  administrator_login_password = var.sql_admin_password
}

# Azure SQL Database — camada gold
resource "azurerm_mssql_database" "licitacoes" {
  name      = "licitacoesdb"
  server_id = azurerm_mssql_server.licitacoes.id
  sku_name  = "Basic"
}

# Firewall rule — permite acesso ao SQL
resource "azurerm_mssql_firewall_rule" "allow_all" {
  name             = "AllowAll"
  server_id        = azurerm_mssql_server.licitacoes.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "255.255.255.255"
}

# Key Vault — cofre de credenciais
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "licitacoes" {
  name                = var.key_vault_name
  location            = azurerm_resource_group.licitacoes.location
  resource_group_name = azurerm_resource_group.licitacoes.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = ["Get", "Set", "List", "Delete", "Purge"]
  }
}

# Guarda a senha do SQL no Key Vault
resource "azurerm_key_vault_secret" "sql_password" {
  name         = "sql-admin-password"
  value        = var.sql_admin_password
  key_vault_id = azurerm_key_vault.licitacoes.id
}

# Azure Data Factory — orquestrador do pipeline
resource "azurerm_data_factory" "licitacoes" {
  name                = var.data_factory_name
  location            = azurerm_resource_group.licitacoes.location
  resource_group_name = azurerm_resource_group.licitacoes.name

  identity {
    type = "SystemAssigned"
  }
}

# Azure Databricks Workspace
resource "azurerm_databricks_workspace" "licitacoes" {
  name                = "licitacoes-databricks"
  resource_group_name = azurerm_resource_group.licitacoes.name
  location            = azurerm_resource_group.licitacoes.location
  sku                 = "trial"
}
