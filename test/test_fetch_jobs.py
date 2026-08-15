from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from ingestion.fetch_jobs import build_raw_key, fetch_jobs, upload_raw

SAMPLE_RESPONSE = [
    {"legal": "notice text"},
    {"id": "123", "position": "Senior Python Engineer", "description": "..."},
    {"id": "456", "position": "React Developer", "description": "..."},
]


@patch("ingestion.fetch_jobs.requests.get")
def test_fetch_jobs_filters_legal_notice(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    jobs = fetch_jobs()

    assert len(jobs) == 2
    assert all("id" in job for job in jobs)


def test_build_raw_key_uses_date_partitions():
    when = datetime(2026, 8, 15, 12, 30, tzinfo=timezone.utc)
    key = build_raw_key(prefix="raw/jobs", when=when)
    assert key == "raw/jobs/2026/08/15/jobs_20260815T123000Z.json"


@patch("ingestion.fetch_jobs.boto3.client")
def test_upload_raw_puts_object_with_expected_key(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    key = upload_raw([{"id": "1"}], bucket="test-bucket", key="raw/jobs/test.json")

    assert key == "raw/jobs/test.json"
    mock_s3.put_object.assert_called_once()
    _, kwargs = mock_s3.put_object.call_args
    assert kwargs["Bucket"] == "test-bucket"
    assert kwargs["Key"] == "raw/jobs/test.json"
