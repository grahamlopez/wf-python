"""Logging module - needs improvement."""

import sys


def log(message):
    print(message, file=sys.stderr)


def log_error(message):
    print(f"ERROR: {message}", file=sys.stderr)
