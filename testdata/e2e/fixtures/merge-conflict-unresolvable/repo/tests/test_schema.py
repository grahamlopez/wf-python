"""Tests for schema module."""

from src.schema import get_user_table


def test_user_table():
    table = get_user_table()
    assert table["name"] == "users"
