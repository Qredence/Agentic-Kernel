"""Ledger for tracking task execution and status.

This module provides a ledger implementation for tracking tasks, their execution
status, results, and performance metrics. It supports concurrent access through
asyncio locks and provides comprehensive task history tracking.

Key features:
    1. Task tracking with unique IDs
    2. Concurrent access support
    3. Task status management
    4. Performance metrics tracking
    5. Task history and export capabilities

Example:
    .. code-block:: python

        # Create a task ledger
        ledger = TaskLedger()

        # Add a task
        task = Task(name="process_data", description="Process input data")
        task_id = await ledger.add_task(task)

        # Update task status
        await ledger.update_task_status(task_id, "completed", {"result": "success"})

        # Export ledger data
        json_data = ledger.export_ledger()
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import json

from ..types import Task


class TaskLedger:
    """Ledger for tracking task execution and status.

    This class provides a thread-safe implementation for tracking tasks,
    their execution results, and performance metrics. It supports concurrent
    access through asyncio locks and provides comprehensive task management
    capabilities.

    Attributes:
        tasks (Dict[str, Task]): Dictionary mapping task IDs to task details.
        task_results (Dict[str, Dict[str, Any]]): Dictionary mapping task IDs to execution results.
        task_metrics (Dict[str, Dict[str, Any]]): Dictionary mapping task IDs to performance metrics.

    Example:
        .. code-block:: python

            # Initialize ledger
            ledger = TaskLedger()

            # Add and track a task
            task = Task(name="analyze_data", parameters={"file": "data.csv"})
            task_id = await ledger.add_task(task)

            # Update task status and results
            await ledger.update_task_status(
                task_id,
                "completed",
                {"processed_rows": 1000}
            )
    """

    def __init__(self):
        """Initialize the task ledger.

        Creates empty dictionaries for tasks, results, and metrics, and
        initializes the asyncio lock for thread-safe operations.
        """
        self.tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, Dict[str, Any]] = {}
        self.task_metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def add_task(self, task: Task) -> str:
        """Add a task to the ledger.

        Args:
            task: Task object to add.

        Returns:
            str: Task ID of the added task.

        Example:
            .. code-block:: python

                task = Task(name="process_file", description="Process data file")
                task_id = await ledger.add_task(task)
        """
        async with self._lock:
            self.tasks[task.id] = task
            return task.id

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.

        Args:
            task_id: ID of the task to retrieve.

        Returns:
            Optional[Task]: Task object if found, None otherwise.

        Example:
            .. code-block:: python

                task = await ledger.get_task("task_123")
                if task:
                    print(f"Task name: {task.name}")
        """
        return self.tasks.get(task_id)

    async def update_task_result(self, task_id: str, result: Dict[str, Any]):
        """Update the result of a task.

        Args:
            task_id: ID of the task.
            result: Task execution result.

        Example:
            .. code-block:: python

                await ledger.update_task_result(
                    "task_123",
                    {"status": "success", "processed_items": 100}
                )
        """
        async with self._lock:
            self.task_results[task_id] = result

    async def update_task_metrics(self, task_id: str, metrics: Dict[str, Any]):
        """Update metrics for a task.

        Args:
            task_id: ID of the task.
            metrics: Task performance metrics.

        Example:
            .. code-block:: python

                await ledger.update_task_metrics(
                    "task_123",
                    {
                        "execution_time": 1.5,
                        "memory_usage": "128MB"
                    }
                )
        """
        async with self._lock:
            self.task_metrics[task_id] = metrics

    async def update_task_status(
        self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None
    ):
        """Update the status and optionally the result of a task.

        Args:
            task_id: ID of the task.
            status: New task status.
            result: Optional task execution result.

        Example:
            .. code-block:: python

                await ledger.update_task_status(
                    "task_123",
                    "completed",
                    {"output": "Task completed successfully"}
                )
        """
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].status = status
                if result:
                    self.task_results[task_id] = result

    async def get_tasks_by_status(self, status: Optional[str] = None) -> List[Task]:
        """Get all tasks with a specific status.

        Args:
            status: Status to filter by, or None to get all tasks.

        Returns:
            List[Task]: List of tasks matching the status.

        Example:
            .. code-block:: python

                # Get all completed tasks
                completed_tasks = await ledger.get_tasks_by_status("completed")
                
                # Get all tasks
                all_tasks = await ledger.get_tasks_by_status()
        """
        if status is None:
            return list(self.tasks.values())
        return [task for task in self.tasks.values() if task.status == status]

    def get_task_history(self, task_id: str) -> Dict[str, Any]:
        """Get the complete history of a task.

        Args:
            task_id: ID of the task.

        Returns:
            Dict[str, Any]: Dictionary containing task details, results, and metrics.

        Example:
            .. code-block:: python

                history = ledger.get_task_history("task_123")
                print(f"Task: {history['task']}")
                print(f"Result: {history['result']}")
                print(f"Metrics: {history['metrics']}")
        """
        return {
            "task": self.tasks.get(task_id),
            "result": self.task_results.get(task_id),
            "metrics": self.task_metrics.get(task_id),
        }

    def export_ledger(self) -> str:
        """Export the ledger data as JSON.

        Returns:
            str: JSON string containing ledger data.

        Example:
            .. code-block:: python

                json_data = ledger.export_ledger()
                with open("ledger_backup.json", "w") as f:
                    f.write(json_data)
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
            task_id: ID of the task.

        Returns:
            Optional[str]: Task status if found, None otherwise.

        Example:
            .. code-block:: python

                status = await ledger.get_task_status("task_123")
                if status:
                    print(f"Task status: {status}")
        """
        task = await self.get_task(task_id)
        return task.status if task else None

    async def clear_completed_tasks(self):
        """Remove completed tasks from the ledger.

        This method removes all completed tasks and their associated
        results and metrics from the ledger.

        Example:
            .. code-block:: python

                await ledger.clear_completed_tasks()
        """
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
            List[Task]: List of active tasks.

        Example:
            .. code-block:: python

                active_tasks = await ledger.get_active_tasks()
                for task in active_tasks:
                    print(f"Active task: {task.name}")
        """
        return [
            task
            for task in self.tasks.values()
            if task.status not in ["completed", "failed"]
        ]
