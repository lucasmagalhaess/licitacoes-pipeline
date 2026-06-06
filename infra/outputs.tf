output "resource_group" {
  value = azurerm_resource_group.licitacoes.name
}

output "storage_account" {
  value = azurerm_storage_account.datalake.name
}

output "sql_server" {
  value = azurerm_mssql_server.licitacoes.fully_qualified_domain_name
}

output "key_vault" {
  value = azurerm_key_vault.licitacoes.name
}

output "data_factory" {
  value = azurerm_data_factory.licitacoes.name
}
