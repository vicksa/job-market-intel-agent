"""Lambda entry point that kicks off one weekly pipeline run.

Triggered weekly by EventBridge (see eventbridge_rule.tf). Responsibilities:
1. Run ingestion (fetch_jobs -> S3 raw).
2. Trigger the Databricks job that runs bronze -> silver -> gold -> report -> Telegram
   via the Databricks Jobs API (that job's last task handles report generation and
   delivery directly on-cluster — see databricks/04_report_and_notify.py — so this
   Lambda doesn't need to wait on it or handle a callback).

The Databricks token is read from AWS Secrets Manager at cold start and cached for
the lifetime of the Lambda execution environment.
"""
from __future__ import annotations

import json
import os

import boto3
import requests

SECRETS_CLIENT = boto3.client("secretsmanager")
DATABRICKS_HOST = os.environ["DATABRICKS_HOST"]
DATABRICKS_JOB_ID = os.environ["DATABRICKS_JOB_ID"]
SECRETS_NAME = os.environ.get("SECRETS_NAME", "job-market-intel-agent/secrets")

_secrets_cache: dict | None = None


def get_secrets() -> dict:
    global _secrets_cache
    if _secrets_cache is None:
        response = SECRETS_CLIENT.get_secret_value(SecretId=SECRETS_NAME)
        _secrets_cache = json.loads(response["SecretString"])
    return _secrets_cache


def trigger_databricks_job(databricks_token: str) -> dict:
    response = requests.post(
        f"{DATABRICKS_HOST}/api/2.1/jobs/run-now",
        headers={"Authorization": f"Bearer {databricks_token}"},
        json={"job_id": DATABRICKS_JOB_ID},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def handler(event, context):
    from ingestion.fetch_jobs import run as run_ingestion

    secrets = get_secrets()
    raw_key = run_ingestion()
    run_response = trigger_databricks_job(secrets["databricks_token"])

    return {
        "statusCode": 200,
        "body": json.dumps({"raw_key": raw_key, "databricks_run": run_response}),
    }
