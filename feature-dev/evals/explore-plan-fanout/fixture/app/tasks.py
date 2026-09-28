"""In-memory task store for the sample task tracker."""

from dataclasses import dataclass, field
from itertools import count

VALID_STATUSES = ("open", "done")

_ids = count(1)


@dataclass
class Task:
    title: str
    status: str = "open"
    id: int = field(default_factory=lambda: next(_ids))


class TaskStore:
    def __init__(self):
        self._tasks = {}

    def add(self, title, status="open"):
        if not title.strip():
            raise ValueError("title must not be empty")
        if status not in VALID_STATUSES:
            raise ValueError(f"unknown status: {status}")
        task = Task(title=title.strip(), status=status)
        self._tasks[task.id] = task
        return task

    def complete(self, task_id):
        self._tasks[task_id].status = "done"
        return self._tasks[task_id]

    def list(self, status=None):
        tasks = sorted(self._tasks.values(), key=lambda t: t.id)
        if status is None:
            return tasks
        return [t for t in tasks if t.status == status]


def serialize(task):
    """Shape returned by the JSON API consumed by web/src/taskList.js."""
    return {"id": task.id, "title": task.title, "status": task.status}
