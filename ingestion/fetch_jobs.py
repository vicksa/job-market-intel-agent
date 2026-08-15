"""Fetch tech job postings from the RemoteOK public API and upload the raw payload to S3."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import boto3
import requests

from ingestion.config import (
    AWS_REGION,
    REMOTEOK_API_URL,
    REQUEST_TIMEOUT_SECONDS,
    S3_BUCKET,
    S3_RAW_PREFIX,
)

logger = logging.getLogger(__name__)

USER_AGENT = "job-market-intel-agent/1.0 (+https://github.com/vicksa/job-market-intel-agent)"


def fetch_jobs(api_url: str = REMOTEOK_API_URL) -> list[dict]:
    """Call the RemoteOK API and return the list of job postings.

    RemoteOK prepends a legal notice as the first element of the response array,
    so entries without an "id" are filtered out.
    """
    response = requests.get(
        api_url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return [item for item in payload if "id" in item]


def build_raw_key(prefix: str = S3_RAW_PREFIX, when: datetime | None = None) -> str:
    when = when or datetime.now(timezone.utc)
    return f"{prefix}/{when:%Y/%m/%d}/jobs_{when:%Y%m%dT%H%M%SZ}.json"


def upload_raw(jobs: list[dict], bucket: str = S3_BUCKET, key: str | None = None) -> str:
    key = key or build_raw_key()
    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(jobs).encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Uploaded %d jobs to s3://%s/%s", len(jobs), bucket, key)
    return key


def run() -> str:
    jobs = fetch_jobs()
    return upload_raw(jobs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
