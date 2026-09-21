from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.table(
    comment=(
        "Bronze Customers (SDP): ingestão incremental de arquivos CSV do volume de "
        "landing via Auto Loader. Colunas: tenant_id, customer_id, effective_at, "
        "plan, city (todas STRING), source_file e ingested_at como metadados."
    )
)
def bronze_customers_sdp():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .load("/Volumes/<UC_CATALOG>/bronze/raw_customer_landing/customers/")
        .withColumn("source_file", F.col("_metadata.file_path"))
        .withColumn("ingested_at", F.current_timestamp())
    )
