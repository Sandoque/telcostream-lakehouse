from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    comment=(
        "Gold KPIs (SDP): agregação de CDR por (tenant_id, cell_tower_id, region, hora_UTC). "
        "Métricas: total_calls, dropped_calls, completed_calls, total_data_mb, "
        "total_sms, avg_duration_sec."
    )
)
def kpi_tower_hourly_sdp():
    return (
        spark.read.table("cdr_silver_sdp")
        .withColumn("hour_start", F.date_trunc("hour", F.col("call_start")))
        .groupBy("tenant_id", "cell_tower_id", "region", "hour_start")
        .agg(
            F.count("*").alias("total_calls"),
            F.sum(
                F.when(F.col("call_status") == "DROPPED",   1).otherwise(0)
            ).alias("dropped_calls"),
            F.sum(
                F.when(F.col("call_status") == "COMPLETED", 1).otherwise(0)
            ).alias("completed_calls"),
            F.sum("data_mb").alias("total_data_mb"),
            F.sum("sms_count").alias("total_sms"),
            F.avg("duration_seconds").alias("avg_duration_sec"),
        )
    )
