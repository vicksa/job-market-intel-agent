"""Bronze layer: read raw job JSON from S3, apply schema, dedupe.

Meant to run as a Databricks job/notebook, where a `spark` SparkSession is already
provided by the runtime. Falls back to building one when run standalone.
"""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import ArrayType, LongType, StringType, StructField, StructType

RAW_PATH = "s3://job-market-intel-agent/raw/jobs/"
BRONZE_PATH = "s3://job-market-intel-agent/bronze/jobs/"

RAW_SCHEMA = StructType(
    [
        StructField("id", StringType(), nullable=False),
        StructField("position", StringType(), nullable=True),
        StructField("company", StringType(), nullable=True),
        StructField("description", StringType(), nullable=True),
        StructField("location", StringType(), nullable=True),
        StructField("tags", ArrayType(StringType()), nullable=True),
        StructField("date", StringType(), nullable=True),
        StructField("salary_min", LongType(), nullable=True),
        StructField("salary_max", LongType(), nullable=True),
    ]
)


def get_spark() -> SparkSession:
    return SparkSession.builder.appName("bronze_ingest").getOrCreate()


def read_raw(spark: SparkSession, path: str = RAW_PATH) -> DataFrame:
    return spark.read.schema(RAW_SCHEMA).json(path)


def validate(raw_df: DataFrame) -> DataFrame:
    return raw_df.dropDuplicates(["id"]).na.drop(subset=["id"])


def run(spark: SparkSession | None = None) -> None:
    spark = spark or get_spark()
    validated_df = validate(read_raw(spark))
    validated_df.write.format("delta").mode("overwrite").save(BRONZE_PATH)


if __name__ == "__main__":
    run()
