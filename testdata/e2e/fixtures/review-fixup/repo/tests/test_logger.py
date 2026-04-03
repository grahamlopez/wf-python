"""Tests for logger module."""

from src.logger import log, log_error


def test_log(capsys):
    log("test message")
    assert "test message" in capsys.readouterr().err
