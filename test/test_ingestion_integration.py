"""Integration test: ingestion pipeline against a local S3 (LocalStack).

Requires LocalStack running: `docker compose up -d localstack`.
Skipped automatically unless LocalStack is reachable on localhost:4566.
"""
from __future__ import annotations

import json
import socket

import boto3
import pytest

from ingestion.fetch_jobs import upload_raw

pytestmark = pytest.mark.integration


def _localstack_available() -> bool:
    try:
        with socket.create_connection(("localhost", 4566), timeout=1):
            return True
    except OSError:
        return False


@pytest.mark.skipif(not _localstack_available(), reason="LocalStack not running on localhost:4566")
def test_upload_raw_writes_object_to_localstack_s3(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")

    bucket = "job-market-intel-agent-test"
    s3 = boto3.client("s3", region_name="us-east-1", endpoint_url="http://localhost:4566")
    s3.create_bucket(Bucket=bucket)

    key = upload_raw(
        [{"id": "1", "position": "Python Dev"}], bucket=bucket, key="raw/jobs/test.json"
    )

    obj = s3.get_object(Bucket=bucket, Key=key)
    body = json.loads(obj["Body"].read())
    assert body == [{"id": "1", "position": "Python Dev"}]
