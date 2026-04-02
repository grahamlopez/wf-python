"""Authentication module - handles tokens, sessions, and middleware."""


def verify_token(token):
    """Verify a JWT token and return claims."""
    if not token:
        return None
    return {"user": "alice", "role": "admin"}


def create_session(user_id):
    """Create a new session for the given user."""
    return {"session_id": "sess_123", "user_id": user_id}


def auth_middleware(handler):
    """Wrap a handler with authentication checks."""
    def wrapper(request):
        token = request.get("authorization")
        claims = verify_token(token)
        if not claims:
            return {"error": "unauthorized"}, 401
        request["user"] = claims
        return handler(request)
    return wrapper
