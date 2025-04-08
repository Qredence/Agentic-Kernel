"""Task management module for the Agentic Kernel system.

This module provides task lifecycle management through the TaskManager class.
It handles task creation, status updates, completion, and failure handling.

Key features:
1. Task creation and tracking
2. Status management
3. Progress monitoring
4. Error handling
5. Task lifecycle events

Typical usage:
    ```python
    task_ledger = TaskLedger()
    progress_ledger = ProgressLedger()
    manager = TaskManager(task_ledger, progress_ledger)
    
    # Create and track a task
    task = manager.create_task(
        description="Process data",
        agent_type="DataProcessor",
        parameters={"input_file": "data.csv"}
    )
    
    # Update task status
    manager.update_task_status(task.id, "running")
    
    # Complete task
    manager.complete_task(task.id, {"result": "success"})
    ```
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, NoReturn, Optional

from .exceptions import TaskNotFoundError
from .ledgers import ProgressLedger, TaskLedger
from .types import Task, TaskStatus

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages tasks and their execution in the Agentic Kernel system.

    This class provides a centralized way to manage tasks throughout their lifecycle.
    It maintains task state, handles status updates, and coordinates with ledgers
    for persistence and progress tracking.

    Attributes:
        task_ledger (TaskLedger): Ledger for persisting task information
        progress_ledger (ProgressLedger): Ledger for tracking task progress
        active_tasks (Dict[str, Task]): Dictionary of currently active tasks

    Example:
        ```python
        manager = TaskManager(task_ledger, progress_ledger)
        task = manager.create_task("Process data", "DataProcessor")
        manager.update_task_status(task.id, "running")
        ```
    """

    def __init__(
        self, task_ledger: TaskLedger, progress_ledger: ProgressLedger
    ) -> None:
        """Initialize the task manager.

        Args:
            task_ledger: Ledger for tracking and persisting tasks
            progress_ledger: Ledger for tracking task progress
        """
        self.task_ledger = task_ledger
        self.progress_ledger = progress_ledger
        self.active_tasks: Dict[str, Task] = {}

    def create_task(
        self,
        description: str,
        agent_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
    ) -> Task:
        """Create a new task and register it with the system.

        This method creates a new task with the given parameters, adds it to both
        the active tasks dictionary and the task ledger for tracking.

        Args:
            description: Human-readable description of the task's purpose
            agent_type: Type of agent that should handle this task
            parameters: Optional parameters needed for task execution
            name: Optional custom name for the task (auto-generated if None)

        Returns:
            The newly created task object

        Example:
            ```python
            task = manager.create_task(
                description="Process customer data",
                agent_type="DataProcessor",
                parameters={"source": "customers.csv"},
                name="process_customers"
            )
            ```
        """
        task = Task(
            name=name or f"task_{uuid.uuid4().hex[:8]}",
            description=description,
            agent_type=agent_type,
            parameters=parameters or {},
        )

        self.task_ledger.add_task(task)
        self.active_tasks[task.id] = task

        logger.info(f"Created task {task.id}: {description}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by its ID.

        Args:
            task_id: The unique identifier of the task

        Returns:
            The task if found, None if not found

        Example:
            ```python
            task = manager.get_task("task_12345678")
            if task:
                print(f"Task status: {task.status}")
            ```
        """
        return self.active_tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """List all tasks, optionally filtered by status.

        Args:
            status: Optional status to filter tasks by

        Returns:
            List of tasks matching the filter criteria

        Example:
            ```python
            # Get all running tasks
            running_tasks = manager.list_tasks(status="running")

            # Get all tasks
            all_tasks = manager.list_tasks()
            ```
        """
        tasks = list(self.active_tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def update_task_status(
        self, task_id: str, status: TaskStatus, output: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update the status and optional output of a task.

        This method updates a task's status and optionally its output. It also
        updates the task's timestamp and persists changes to the task ledger.

        Args:
            task_id: The unique identifier of the task to update
            status: The new status to set
            output: Optional output data from task execution

        Raises:
            TaskNotFoundError: If the specified task is not found

        Example:
            ```python
            try:
                manager.update_task_status(
                    task_id="task_12345678",
                    status="running",
                    output={"progress": 0.5}
                )
            except TaskNotFoundError:
                logger.error("Task not found")
            ```
        """
        task = self.get_task(task_id)
        if not task:
            raise TaskNotFoundError(f"Task not found: {task_id}")

        task.status = status
        task.output = output
        task.updated_at = datetime.now().isoformat()

        self.task_ledger.update_task(task)
        logger.info(f"Updated task {task_id} status to {status}")

    def complete_task(self, task_id: str, output: Dict[str, Any]) -> None:
        """Mark a task as completed with its final output.

        This method updates the task's status to completed, stores its output,
        and removes it from the active tasks list.

        Args:
            task_id: The unique identifier of the task to complete
            output: The final output data from task execution

        Raises:
            TaskNotFoundError: If the specified task is not found
        """
        self.update_task_status(task_id, "completed", output)
        self.active_tasks.pop(task_id, None)

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark a task as failed with an error message.

        This method updates the task's status to failed, stores the error message,
        and removes it from the active tasks list.

        Args:
            task_id: The unique identifier of the task that failed
            error: Description of what went wrong

        Raises:
            TaskNotFoundError: If the specified task is not found
        """
        self.update_task_status(task_id, "failed", {"error": error, "output": None})
        self.active_tasks.pop(task_id, None)

    def cancel_task(self, task_id: str) -> None:
        """Cancel a task and mark it as cancelled.

        This method updates the task's status to cancelled and removes it
        from the active tasks list.

        Args:
            task_id: The unique identifier of the task to cancel

        Raises:
            TaskNotFoundError: If the specified task is not found
        """
        self.update_task_status(
            task_id, "cancelled", {"error": "Task cancelled", "output": None}
        )
        self.active_tasks.pop(task_id, None)
