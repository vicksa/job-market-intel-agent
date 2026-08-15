"""Environment-driven configuration for the ingestion step."""
import os

REMOTEOK_API_URL = os.environ.get("REMOTEOK_API_URL", "https://remoteok.com/api")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET = os.environ.get("S3_BUCKET", "job-market-intel-agent")
S3_RAW_PREFIX = os.environ.get("S3_RAW_PREFIX", "raw/jobs")
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "15"))
