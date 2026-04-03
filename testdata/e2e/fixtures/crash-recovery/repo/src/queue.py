"""Simple job queue."""


class JobQueue:
    def __init__(self):
        self._jobs = []

    def push(self, job):
        self._jobs.append(job)

    def pop(self):
        return self._jobs.pop(0) if self._jobs else None
