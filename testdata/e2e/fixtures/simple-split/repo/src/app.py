"""Simple web app - monolithic module to be split."""


def handle_request(path):
    """Route a request to the appropriate handler."""
    if path == "/users":
        return list_users()
    elif path == "/health":
        return health_check()
    return {"error": "not found"}, 404


def list_users():
    return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], 200


def health_check():
    return {"status": "ok"}, 200
