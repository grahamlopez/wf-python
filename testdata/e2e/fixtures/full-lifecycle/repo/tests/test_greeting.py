"""Tests for greeting module."""

from src.greeting import greet, farewell


def test_greet():
    assert greet("Alice") == "Hello, Alice!"


def test_farewell():
    assert farewell("Alice") == "Goodbye, Alice!"
