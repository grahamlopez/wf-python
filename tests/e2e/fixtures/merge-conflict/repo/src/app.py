"""Main application module."""

from src.constants import VERSION, APP_NAME, TIMEOUT


def get_info():
    return {"name": APP_NAME, "version": VERSION, "timeout": TIMEOUT}
