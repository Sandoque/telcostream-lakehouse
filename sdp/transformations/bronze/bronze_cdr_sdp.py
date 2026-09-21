from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.table(
    comment=(
        "Bronze CDR (SDP): ingestão incremental de arquivos JSON do volume de landing "
        "via Auto Loader. Preserva todas as colunas originais e adiciona metadados "
        "de ingestão (source_file, ingested_at)."
    )
)
def bronze_cdr_sdp():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .load("/Volumes/<UC_CATALOG>/bronze/raw_cdr_landing/cdr/")
        .withColumn("source_file", F.col("_metadata.file_path"))
        .withColumn("ingested_at", F.current_timestamp())
    )
