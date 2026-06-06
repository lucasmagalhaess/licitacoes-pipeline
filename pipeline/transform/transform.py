from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, datediff, to_date, round as spark_round,
    avg, count, lit, current_date
)
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
import json
import sys

def classificar_valor(valor):
    return when(valor >= 10000000, "mega") \
           .when(valor >= 1000000, "grande") \
           .when(valor >= 100000, "medio") \
           .otherwise("pequeno")

def transform(blob_path, output_path):
    spark = SparkSession.builder \
        .appName("licitacoes-transform") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    print(f"Lendo dados do bronze: {blob_path}")
    df_raw = spark.read.option("multiline", "true").json(blob_path)

    # Explode o array de contratos
    from pyspark.sql.functions import explode
    df = df_raw.select(explode("contratos").alias("contrato"))

    # Extrai os campos relevantes
    df = df.select(
        col("contrato.id").alias("id"),
        col("contrato.numero").alias("numero"),
        col("contrato.objeto").alias("objeto"),
        col("contrato.orgao_nome").alias("orgao_nome"),
        col("contrato.orgao_codigo").alias("orgao_codigo"),
        col("contrato.situacaoContrato").alias("situacao"),
        col("contrato.dataAssinatura").alias("data_assinatura"),
        col("contrato.dataInicioVigencia").alias("data_inicio_vigencia"),
        col("contrato.dataFimVigencia").alias("data_fim_vigencia"),
        col("contrato.valorInicialCompra").cast("double").alias("valor_inicial"),
        col("contrato.valorFinalCompra").cast("double").alias("valor_final"),
        col("contrato.fornecedor.nome").alias("fornecedor_nome"),
        col("contrato.fornecedor.cnpjFormatado").alias("fornecedor_cnpj"),
        col("contrato.extraction_date").alias("extraction_date"),
    )

    # Transformações silver
    df_silver = df \
        .withColumn("classificacao_valor", classificar_valor(col("valor_final"))) \
        .withColumn("variacao_valor",
            spark_round((col("valor_final") - col("valor_inicial")) / col("valor_inicial") * 100, 2)) \
        .withColumn("duracao_dias",
            datediff(to_date(col("data_fim_vigencia")), to_date(col("data_inicio_vigencia")))) \
        .withColumn("status_vigencia",
            when(to_date(col("data_fim_vigencia")) < current_date(), "encerrado")
            .when(to_date(col("data_fim_vigencia")) >= current_date(), "vigente")
            .otherwise("indefinido"))

    print(f"Registros transformados: {df_silver.count()}")
    print("\nDistribuição por classificação:")
    df_silver.groupBy("classificacao_valor").count().show()

    print("\nValor médio por órgão:")
    df_silver.groupBy("orgao_nome") \
        .agg(
            avg("valor_final").alias("valor_medio"),
            count("id").alias("total_contratos")
        ) \
        .orderBy("valor_medio", ascending=False) \
        .show(truncate=False)

    # Salva como Parquet no silver
    df_silver.write \
        .mode("overwrite") \
        .parquet(output_path)

    print(f"\nSalvo no silver: {output_path}")
    spark.stop()
    return df_silver

if __name__ == "__main__":
    blob_path = sys.argv[1] if len(sys.argv) > 1 else None
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not blob_path or not output_path:
        print("Uso: python transform.py <blob_path> <output_path>")
        sys.exit(1)

    transform(blob_path, output_path)
