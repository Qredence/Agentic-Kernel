"""Ledger for tracking task execution and status."""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import json

from ..types import Task


class TaskLedger:
    """Ledger for tracking task execution and status.

    Attributes:
        tasks: Dictionary mapping task IDs to task details
        task_results: Dictionary mapping task IDs to execution results
        task_metrics: Dictionary mapping task IDs to performance metrics
    """

    def __init__(self):
        """Initialize the task ledger."""
        self.tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, Dict[str, Any]] = {}
        self.task_metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def add_task(self, task: Task) -> str:
        """Add a task to the ledger.

        Args:
            task: Task object to add

        Returns:
            Task ID
        """
        async with self._lock:
            self.tasks[task.id] = task
            return task.id

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.

        Args:
            task_id: ID of the task to retrieve

        Returns:
            Task object if found, None otherwise
        """
        return self.tasks.get(task_id)

    async def update_task_result(self, task_id: str, result: Dict[str, Any]):
        """Update the result of a task.

        Args:
            task_id: ID of the task
            result: Task execution result
        """
        async with self._lock:
            self.task_results[task_id] = result

    async def update_task_metrics(self, task_id: str, metrics: Dict[str, Any]):
        """Update metrics for a task.

        Args:
            task_id: ID of the task
            metrics: Task performance metrics
        """
        async with self._lock:
            self.task_metrics[task_id] = metrics

    async def update_task_status(
        self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None
    ):
        """Update the status and optionally the result of a task.

        Args:
            task_id: ID of the task
            status: New task status
            result: Optional task execution result
        """
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].status = status
                if result:
                    self.task_results[task_id] = result

    async def get_tasks_by_status(self, status: Optional[str] = None) -> List[Task]:
        """Get all tasks with a specific status.

        Args:
            status: Status to filter by, or None to get all tasks

        Returns:
            List of tasks matching the status
        """
        if status is None:
            return list(self.tasks.values())
        return [task for task in self.tasks.values() if task.status == status]

    def get_task_history(self, task_id: str) -> Dict[str, Any]:
        """Get the complete history of a task.

        Args:
            task_id: ID of the task

        Returns:
            Dictionary containing task details, results, and metrics
        """
        return {
            "task": self.tasks.get(task_id),
            "result": self.task_results.get(task_id),
            "metrics": self.task_metrics.get(task_id),
        }

    def export_ledger(self) -> str:
        """Export the ledger data as JSON.

        Returns:
            JSON string containing ledger data
        """
        data = {
            "tasks": {k: v.dict() for k, v in self.tasks.items()},
            "results": self.task_results,
            "metrics": self.task_metrics,
        }
        return json.dumps(data, indent=2)

    async def get_task_status(self, task_id: str) -> Optional[str]:
        """Get the status of a task.

        Args:
            task_id: ID of the task

        Returns:
            Task status if found, None otherwise
        """
        task = await self.get_task(task_id)
        return task.status if task else None

    async def clear_completed_tasks(self):
        """Remove completed tasks from the ledger."""
        async with self._lock:
            completed_tasks = [
                task_id
                for task_id, task in self.tasks.items()
                if task.status == "completed"
            ]
            for task_id in completed_tasks:
                del self.tasks[task_id]
                self.task_results.pop(task_id, None)
                self.task_metrics.pop(task_id, None)

    async def get_active_tasks(self) -> List[Task]:
        """Get all tasks that are not completed or failed.

        Returns:
            List of active tasks
        """
        return [
            task
            for task in self.tasks.values()
            if task.status not in ["completed", "failed"]
        ]
