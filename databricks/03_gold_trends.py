"""Gold layer: aggregate skill counts per week and diff against the prior week."""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

SILVER_PATH = "s3://job-market-intel-agent/silver/jobs/"
GOLD_PATH = "s3://job-market-intel-agent/gold/trends/"


def get_spark() -> SparkSession:
    return SparkSession.builder.appName("gold_trends").getOrCreate()


def weekly_skill_counts(silver_df: DataFrame) -> DataFrame:
    return (
        silver_df.withColumn("skill", F.explode("skills"))
        .groupBy("ingest_week", "skill")
        .agg(F.count("*").alias("job_count"))
    )


def week_over_week_trends(skill_counts: DataFrame) -> DataFrame:
    window = Window.partitionBy("skill").orderBy("ingest_week")
    return (
        skill_counts.withColumn("prev_week_count", F.lag("job_count").over(window))
        .withColumn(
            "delta",
            F.col("job_count") - F.coalesce(F.col("prev_week_count"), F.lit(0)),
        )
        .withColumn(
            "status",
            F.when(F.col("prev_week_count").isNull(), F.lit("new"))
            .when(F.col("delta") > 0, F.lit("up"))
            .when(F.col("delta") < 0, F.lit("down"))
            .otherwise(F.lit("flat")),
        )
    )


def run(spark: SparkSession | None = None) -> None:
    spark = spark or get_spark()
    silver_df = spark.read.format("delta").load(SILVER_PATH)
    trends_df = week_over_week_trends(weekly_skill_counts(silver_df))
    trends_df.write.format("delta").mode("overwrite").save(GOLD_PATH)


if __name__ == "__main__":
    run()
