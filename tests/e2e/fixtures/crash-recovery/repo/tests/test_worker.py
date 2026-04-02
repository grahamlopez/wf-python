"""Tests for worker module."""

from src.worker import process_job


def test_process_job():
    result = process_job("job-1")
    assert result["status"] == "completed"
