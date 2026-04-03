"""Database schema definition."""


def get_user_table():
    return {
        "name": "users",
        "columns": [
            {"name": "id", "type": "INTEGER", "primary": True},
            {"name": "name", "type": "TEXT"},
            {"name": "email", "type": "TEXT"},
        ]
    }
