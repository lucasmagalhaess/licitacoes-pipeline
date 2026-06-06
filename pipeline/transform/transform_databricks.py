# Notebook PySpark — Databricks
# Roda no Azure Databricks conectado ao Blob Storage e Azure SQL

import requests
import json
from pyspark.sql.functions import col, when, datediff, to_date, current_date, round as spark_round, avg, count
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

# Configurações
storage_account = "licitacoesdatalake"
sas_token = dbutils.secrets.get(scope="licitacoes", key="sas-token")
server = "licitacoes-sql-server.database.windows.net"
database = "licitacoesdb"
username = "adminlicitacoes"
password = dbutils.secrets.get(scope="licitacoes", key="sql-password")

# Lê bronze do Blob Storage
blob_date = "2026-06-06"
blob_file = "contratos_2026-06-06T04-11-33.json"
url = "https://" + storage_account + ".blob.core.windows.net/bronze/licitacoes/" + blob_date + "/" + blob_file + "?" + sas_token

response = requests.get(url)
data = response.json()
contratos = data["contratos"]
print("Total contratos bronze: " + str(len(contratos)))

# Cria DataFrame PySpark
rows = []
for c in contratos:
    rows.append((
        str(c.get("id", "")),
        str(c.get("numero", "")),
        str(c.get("objeto", ""))[:200],
        str(c.get("orgao_nome", "")),
        str(c.get("orgao_codigo", "")),
        str(c.get("situacaoContrato", "")),
        str(c.get("dataAssinatura", "")),
        str(c.get("dataInicioVigencia", "")),
        str(c.get("dataFimVigencia", "")),
        float(c.get("valorInicialCompra") or 0),
        float(c.get("valorFinalCompra") or 0),
        str(c.get("fornecedor", {}).get("nome", "")),
        str(c.get("fornecedor", {}).get("cnpjFormatado", "")),
        str(c.get("extraction_date", ""))
    ))

schema = StructType([
    StructField("id", StringType()),
    StructField("numero", StringType()),
    StructField("objeto", StringType()),
    StructField("orgao_nome", StringType()),
    StructField("orgao_codigo", StringType()),
    StructField("situacao", StringType()),
    StructField("data_assinatura", StringType()),
    StructField("data_inicio_vigencia", StringType()),
    StructField("data_fim_vigencia", StringType()),
    StructField("valor_inicial", DoubleType()),
    StructField("valor_final", DoubleType()),
    StructField("fornecedor_nome", StringType()),
    StructField("fornecedor_cnpj", StringType()),
    StructField("extraction_date", StringType()),
])

df = spark.createDataFrame(rows, schema)

# Transformações silver
df_silver = df \
    .withColumn("classificacao_valor",
        when(col("valor_final") >= 10000000, "mega")
        .when(col("valor_final") >= 1000000, "grande")
        .when(col("valor_final") >= 100000, "medio")
        .otherwise("pequeno")) \
    .withColumn("variacao_valor",
        spark_round((col("valor_final") - col("valor_inicial")) / col("valor_inicial") * 100, 2)) \
    .withColumn("duracao_dias",
        datediff(to_date(col("data_fim_vigencia")), to_date(col("data_inicio_vigencia")))) \
    .withColumn("status_vigencia",
        when(to_date(col("data_fim_vigencia")) < current_date(), "encerrado")
        .when(to_date(col("data_fim_vigencia")) >= current_date(), "vigente")
        .otherwise("indefinido"))

print("Transformacoes aplicadas: " + str(df_silver.count()) + " registros")

# Salva silver no Blob Storage
from azure.storage.blob import BlobServiceClient
output_data = [row.asDict() for row in df_silver.collect()]
silver_json = "\n".join([json.dumps(r, ensure_ascii=False) for r in output_data])
storage_key = dbutils.secrets.get(scope="licitacoes", key="storage-key")
full_conn_str = "DefaultEndpointsProtocol=https;AccountName=" + storage_account + ";AccountKey=" + storage_key + ";EndpointSuffix=core.windows.net"
client = BlobServiceClient.from_connection_string(full_conn_str)
client.get_container_client("silver").upload_blob(
    name="licitacoes/" + blob_date + "/contratos_silver.ndjson",
    data=silver_json.encode("utf-8"),
    overwrite=True
)
print("Silver salvo no Blob Storage!")

# Carrega gold no Azure SQL
df_silver.write \
    .format("sqlserver") \
    .option("host", server) \
    .option("port", "1433") \
    .option("database", database) \
    .option("user", username) \
    .option("password", password) \
    .option("dbtable", "contratos_gold") \
    .mode("overwrite") \
    .save()

print("Gold carregado no Azure SQL Database!")
print("Pipeline completo!")
