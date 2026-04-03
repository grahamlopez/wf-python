"""Basic tests for app module."""

from src.app import handle_request


def test_health():
    body, status = handle_request("/health")
    assert status == 200
