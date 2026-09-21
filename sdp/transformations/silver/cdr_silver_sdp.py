from pyspark import pipelines as dp
from pyspark.sql import functions as F, Window


# Nota: a validação de customer_id é feita via left_semi join na query
# (expectations não suportam subqueries). Os demais checks usam expect_or_drop.
@dp.materialized_view(
    comment=(
        "Silver CDR (SDP): registros deduplidos por (tenant_id, call_id) mantendo "
        "maior event_version, colunas tipadas (timestamps, double, int) e "
        "validadas por Expectations. Registros com customer_id desconhecido "
        "são filtrados por semi-join antes das Expectations."
    )
)
@dp.expect_all_or_drop({
    "call_id not null":          "call_id IS NOT NULL",
    "call_end after call_start": "call_end > call_start",
    "data_mb non-negative":      "data_mb >= 0.0",
})
def cdr_silver_sdp():
    # Clientes válidos para filtro de customer_id desconhecido
    valid_customers = (
        spark.read.table("bronze_customers_sdp")
        .select("customer_id")
        .distinct()
    )

    # Deduplicar: maior event_version por (tenant_id, call_id)
    w = Window.partitionBy("tenant_id", "call_id").orderBy(
        F.desc(F.col("event_version").cast("int"))
    )

    return (
        spark.read.table("bronze_cdr_sdp")
        .withColumn("rn", F.row_number().over(w))
        .filter(F.col("rn") == 1)
        .drop("rn")
        # Tipagem das colunas de negócio
        .withColumn("event_version",    F.col("event_version").cast("int"))
        .withColumn("call_start",       F.to_timestamp("call_start"))
        .withColumn("call_end",         F.to_timestamp("call_end"))
        .withColumn("data_mb",          F.col("data_mb").cast("double"))
        .withColumn("sms_count",        F.col("sms_count").cast("int"))
        .withColumn(
            "duration_seconds",
            F.unix_timestamp("call_end") - F.unix_timestamp("call_start"),
        )
        # Filtrar registros com customer_id desconhecido (left semi join)
        .join(valid_customers, on="customer_id", how="left_semi")
    )
