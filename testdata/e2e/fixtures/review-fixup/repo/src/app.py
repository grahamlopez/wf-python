"""Main application with logging."""

from src.logger import log, log_error


def run():
    log("Starting application")
    try:
        result = do_work()
        log(f"Work completed: {result}")
    except Exception as e:
        log_error(str(e))


def do_work():
    return {"status": "ok"}
