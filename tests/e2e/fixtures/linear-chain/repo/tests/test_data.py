"""Tests for data pipeline."""

from src.data import process


def test_process():
    assert process("hello\nworld") == "HELLO\nWORLD"
