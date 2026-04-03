"""Tests for auth module."""

from src.auth import verify_token


def test_verify_valid_token():
    assert verify_token("valid") is not None


def test_verify_empty_token():
    assert verify_token("") is None
