"""Final task of the weekly Databricks job: turn gold trends into a report and send it.

Runs on the same cluster right after 03_gold_trends.py, so it reads the gold table
directly instead of round-tripping through Lambda. Requires `anthropic` and
`requests` as cluster libraries, and the LLM/Telegram credentials as Databricks
secrets (see infra/secrets_setup.md).
"""
from __future__ import annotations

from datetime import date, timedelta

from pyspark.sql import SparkSession

from agent.report_generator import generate_report
from delivery.telegram_notifier import send_report

GOLD_PATH = "s3://job-market-intel-agent/gold/trends/"


def get_spark() -> SparkSession:
    return SparkSession.builder.appName("report_and_notify").getOrCreate()


def current_week_trends(spark: SparkSession, gold_path: str = GOLD_PATH) -> list[dict]:
    gold_df = spark.read.format("delta").load(gold_path)
    latest_week = gold_df.selectExpr("max(ingest_week) as w").first()["w"]
    return [row.asDict() for row in gold_df.filter(gold_df.ingest_week == latest_week).collect()]


def run(spark: SparkSession | None = None) -> None:
    spark = spark or get_spark()
    trends = current_week_trends(spark)
    week_label = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    report = generate_report(trends, week=week_label)
    send_report(report)


if __name__ == "__main__":
    run()
