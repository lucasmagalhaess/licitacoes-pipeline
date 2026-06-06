variable "resource_group_name" {
  default = "licitacoes-pipeline-rg"
}

variable "location" {
  default = "brazilsouth"
}

variable "storage_account_name" {
  default = "licitacoesdatalake"
}

variable "sql_server_name" {
  default = "licitacoes-sql-server"
}

variable "sql_admin_login" {
  default = "adminlicitacoes"
}

variable "sql_admin_password" {
  default = "LicitacoesPipeline2026!"
}

variable "key_vault_name" {
  default = "licitacoes-kv-2026"
}

variable "data_factory_name" {
  default = "licitacoes-adf"
}
