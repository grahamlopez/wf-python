"""Tests for app module."""

from src.app import get_info


def test_get_info():
    info = get_info()
    assert info["name"] == "myapp"
