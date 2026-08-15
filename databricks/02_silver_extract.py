"""Silver layer: extract skills, seniority and work mode from bronze job postings.

Skill matching uses a fixed known-skills list against the job text (position +
description), running distributed via a Spark UDF. See README for the trade-off
against LLM-based extraction.
"""
from __future__ import annotations

import re

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType

BRONZE_PATH = "s3://job-market-intel-agent/bronze/jobs/"
SILVER_PATH = "s3://job-market-intel-agent/silver/jobs/"

KNOWN_SKILLS = [
    "python", "javascript", "typescript", "java", "go", "rust", "c#", "c++",
    "react", "vue", "angular", "node.js", "django", "flask", "fastapi",
    "spring", "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "postgresql", "mysql", "mongodb", "redis", "spark", "databricks",
    "airflow", "kafka", "graphql", "rest", "sql", "pandas", "pytorch",
    "tensorflow", "ci/cd", "git",
]

SENIORITY_PATTERNS = {
    "junior": r"\b(junior|jr\.?)\b",
    "pleno": r"\b(pleno|mid[- ]level|intermediate)\b",
    "senior": r"\b(senior|sr\.?|staff|principal|lead)\b",
}

WORK_MODE_PATTERNS = {
    "remote": r"\b(remote|remoto|work from home|wfh)\b",
    "hybrid": r"\b(hybrid|h[ií]brido)\b",
    "onsite": r"\b(onsite|on-site|presencial|in[- ]office)\b",
}


def extract_skills(text: str | None) -> list[str]:
    text_lower = (text or "").lower()
    return sorted({skill for skill in KNOWN_SKILLS if skill in text_lower})


def extract_seniority(text: str | None) -> str:
    text_lower = (text or "").lower()
    for level, pattern in SENIORITY_PATTERNS.items():
        if re.search(pattern, text_lower):
            return level
    return "unspecified"


def extract_work_mode(text: str | None) -> str:
    text_lower = (text or "").lower()
    for mode, pattern in WORK_MODE_PATTERNS.items():
        if re.search(pattern, text_lower):
            return mode
    return "unspecified"


extract_skills_udf = F.udf(extract_skills, ArrayType(StringType()))
extract_seniority_udf = F.udf(extract_seniority, StringType())
extract_work_mode_udf = F.udf(extract_work_mode, StringType())


def get_spark() -> SparkSession:
    return SparkSession.builder.appName("silver_extract").getOrCreate()


def enrich(bronze_df: DataFrame) -> DataFrame:
    text_col = F.concat_ws(" ", F.col("position"), F.col("description"))
    return (
        bronze_df.withColumn("skills", extract_skills_udf(text_col))
        .withColumn("seniority", extract_seniority_udf(text_col))
        .withColumn("work_mode", extract_work_mode_udf(text_col))
        .withColumn("ingest_week", F.date_trunc("week", F.to_date("date")))
    )


def run(spark: SparkSession | None = None) -> None:
    spark = spark or get_spark()
    bronze_df = spark.read.format("delta").load(BRONZE_PATH)
    enrich(bronze_df).write.format("delta").mode("overwrite").save(SILVER_PATH)


if __name__ == "__main__":
    run()
