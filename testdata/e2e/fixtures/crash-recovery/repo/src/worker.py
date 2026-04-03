"""Worker module for background processing."""


def process_job(job_id):
    """Process a single background job."""
    return {"job_id": job_id, "status": "completed"}


def list_pending():
    """List all pending jobs."""
    return []
