"""Task management utilities.

This module provides utilities for managing tasks, including creation,
tracking, and synchronization with the Chainlit UI. It supports task
lifecycle management and progress tracking through ledgers.

Key features:
    1. Task creation and tracking
    2. Status management and updates
    3. Progress monitoring
    4. Chainlit UI integration
    5. Metrics collection

Example:
    .. code-block:: python

        # Initialize managers
        task_ledger = TaskLedger()
        progress_ledger = ProgressLedger()
        manager = TaskManager(task_ledger, progress_ledger)

        # Create and track a task
        task = await manager.create_task(
            name="process_data",
            agent_type="data_processor",
            description="Process input files"
        )

        # Update task status
        await manager.update_task_status(
            task.id,
            "completed",
            {"processed_files": 10}
        )
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..ledgers.progress_ledger import ProgressLedger
from ..ledgers.task_ledger import TaskLedger
from ..types import Task

# Try importing Chainlit, but allow tests to run without it
try:
    import chainlit as cl

    CHAINLIT_AVAILABLE = True
except ImportError:
    CHAINLIT_AVAILABLE = False
    cl = None

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages task creation, assignment, and tracking, including Chainlit UI sync.

    This class provides a comprehensive interface for managing tasks throughout
    their lifecycle. It handles task creation, status updates, progress tracking,
    and synchronization with the Chainlit UI for visualization.

    Attributes:
        task_ledger (TaskLedger): The task ledger for task tracking.
        progress_ledger (ProgressLedger): The progress ledger for progress tracking.
        tasks (Dict[str, Task]): Dictionary mapping task IDs to task objects.
        message_task_map (Dict[str, str]): Dictionary mapping Chainlit message IDs to task IDs.

    Example:
        .. code-block:: python

            # Initialize the manager
            manager = TaskManager(task_ledger, progress_ledger)

            # Create a task
            task = await manager.create_task(
                name="analyze_data",
                agent_type="data_analyzer",
                parameters={"file": "data.csv"}
            )

            # Update progress
            await manager.update_task_status(
                task.id,
                "running",
                progress={"percent_complete": 50}
            )

            # Complete the task
            await manager.complete_task(
                task.id,
                result={"analysis": "completed"},
                metrics={"execution_time": 1.5}
            )
    """

    def __init__(
        self, task_ledger: TaskLedger, progress_ledger: ProgressLedger
    ) -> None:
        """Initialize the TaskManager.

        Args:
            task_ledger: The task ledger to use for task tracking.
            progress_ledger: The progress ledger to use for progress tracking.

        Example:
            .. code-block:: python

                task_ledger = TaskLedger()
                progress_ledger = ProgressLedger()
                manager = TaskManager(task_ledger, progress_ledger)
        """
        self.task_ledger = task_ledger
        self.progress_ledger = progress_ledger
        self.tasks: Dict[str, Task] = {}
        self.message_task_map: Dict[str, str] = {}
        logger.info("TaskManager initialized with task and progress ledgers.")

    async def create_task(
        self,
        name: str,
        agent_type: str,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout: Optional[float] = None,
    ) -> Task:
        """Create a new task.

        Args:
            name: Name of the task.
            agent_type: Type of agent to execute the task.
            description: Optional description of the task.
            parameters: Optional parameters for task execution.
            max_retries: Maximum number of retry attempts.
            timeout: Maximum time in seconds for execution.

        Returns:
            Task: The created task object.

        Example:
            .. code-block:: python

                task = await manager.create_task(
                    name="process_data",
                    agent_type="data_processor",
                    description="Process input files",
                    parameters={"input_dir": "data/"},
                    max_retries=3,
                    timeout=300
                )
        """
        task = Task(
            name=name,
            agent_type=agent_type,
            description=description,
            parameters=parameters or {},
            max_retries=max_retries,
            timeout=timeout,
        )

        await self.task_ledger.add_task(task)
        logger.info(f"Created task {task.id} of type {agent_type}")
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.

        Args:
            task_id: ID of the task.

        Returns:
            Optional[Task]: The task if found, None otherwise.

        Example:
            .. code-block:: python

                task = await manager.get_task("task_123")
                if task:
                    print(f"Task status: {task.status}")
        """
        return await self.task_ledger.get_task(task_id)

    async def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        """List tasks, optionally filtered by status.

        Args:
            status: Optional status to filter by.

        Returns:
            List[Task]: List of matching tasks.

        Example:
            .. code-block:: python

                # Get all running tasks
                running_tasks = await manager.list_tasks("running")

                # Get all tasks
                all_tasks = await manager.list_tasks()
        """
        return await self.task_ledger.get_tasks_by_status(status)

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        progress: Optional[Dict[str, Any]] = None,
    ):
        """Update the status of a task.

        Args:
            task_id: ID of the task.
            status: New status value.
            result: Optional result data.
            progress: Optional progress data.

        Example:
            .. code-block:: python

                await manager.update_task_status(
                    "task_123",
                    "running",
                    progress={"percent_complete": 75}
                )
        """
        await self.task_ledger.update_task_status(task_id, status, result)
        if progress:
            await self.progress_ledger.record_progress(task_id, progress)
        logger.info(f"Updated task {task_id} status to {status}")

    async def complete_task(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ):
        """Mark a task as completed.

        Args:
            task_id: ID of the task.
            result: Optional result data.
            metrics: Optional metrics data.

        Example:
            .. code-block:: python

                await manager.complete_task(
                    "task_123",
                    result={"output": "Task completed successfully"},
                    metrics={"execution_time": 2.5}
                )
        """
        await self.update_task_status(task_id, "completed", result)
        if metrics:
            await self.progress_ledger.record_progress(
                task_id,
                {
                    "status": "completed",
                    "metrics": metrics,
                    "completed_at": datetime.utcnow().isoformat(),
                },
            )
        logger.info(f"Completed task {task_id}")

    async def fail_task(
        self, task_id: str, error: str, metrics: Optional[Dict[str, Any]] = None
    ):
        """Mark a task as failed.

        Args:
            task_id: ID of the task.
            error: Error message.
            metrics: Optional metrics data.

        Example:
            .. code-block:: python

                await manager.fail_task(
                    "task_123",
                    "Input file not found",
                    metrics={"attempt": 3}
                )
        """
        await self.update_task_status(task_id, "failed", {"error": error})
        if metrics:
            await self.progress_ledger.record_progress(
                task_id,
                {
                    "status": "failed",
                    "error": error,
                    "metrics": metrics,
                    "failed_at": datetime.utcnow().isoformat(),
                },
            )
        logger.info(f"Failed task {task_id}: {error}")

    async def cancel_task(self, task_id: str):
        """Cancel a task.

        Args:
            task_id: ID of the task.

        Example:
            .. code-block:: python

                await manager.cancel_task("task_123")
        """
        await self.update_task_status(task_id, "cancelled")
        await self.progress_ledger.record_progress(
            task_id,
            {"status": "cancelled", "cancelled_at": datetime.utcnow().isoformat()},
        )
        logger.info(f"Cancelled task {task_id}")

    async def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get progress data for a task.

        Args:
            task_id: ID of the task.

        Returns:
            Optional[Dict[str, Any]]: Progress data if found, None otherwise.

        Example:
            .. code-block:: python

                progress = await manager.get_task_progress("task_123")
                if progress:
                    print(f"Progress: {progress['status']}")
        """
        return await self.progress_ledger.get_progress(task_id)

    async def link_message_to_task(self, message_id: str, task_id: str) -> None:
        """Link a Chainlit message ID to a task ID for tracking purposes.

        Args:
            message_id: The ID of the Chainlit message.
            task_id: The ID of the task associated with the message.

        Example:
            .. code-block:: python

                await manager.link_message_to_task(
                    "msg_123",
                    "task_456"
                )
        """
        if not CHAINLIT_AVAILABLE:
            return

        if task_id not in self.tasks:
            logger.warning(
                f"Cannot link message '{message_id}' to non-existent task '{task_id}'."
            )
            return

        self.message_task_map[message_id] = task_id
        logger.debug(f"Linked message '{message_id}' to task '{task_id}'.")

    async def sync_with_chainlit_tasklist(
        self, task_list: Optional["cl.TaskList"]
    ) -> None:
        """Sync the current tasks with a Chainlit TaskList UI element.

        Args:
            task_list: The Chainlit TaskList object to sync with.

        Example:
            .. code-block:: python

                task_list = cl.TaskList()
                await manager.sync_with_chainlit_tasklist(task_list)
        """
        if not CHAINLIT_AVAILABLE or not task_list:
            return

        logger.debug("Syncing TaskManager with Chainlit TaskList.")

        # Use a temporary list to avoid modifying while iterating
        current_cl_tasks = list(task_list.tasks)
        task_list.tasks.clear()

        # Add tasks from the manager
        for task_id, task in self.tasks.items():
            if task.status == "pending":
                cl_status = cl.TaskStatus.RUNNING
            elif task.status == "completed":
                cl_status = cl.TaskStatus.DONE
            elif task.status == "failed":
                cl_status = cl.TaskStatus.FAILED
            else:  # includes 'running' or any other custom status
                cl_status = cl.TaskStatus.RUNNING

            cl_task = cl.Task(
                title=f"{task.name}: {task.description[:50]}...", status=cl_status
            )

            # If task is linked to a message, set the forId
            for msg_id, linked_task_id in self.message_task_map.items():
                if linked_task_id == task_id:
                    cl_task.forId = msg_id
                    break

            task_list.tasks.append(cl_task)

        # Update task list status based on overall task statuses
        pending_tasks = any(
            t.status == "pending" or t.status == "running" for t in self.tasks.values()
        )
        failed_tasks = any(t.status == "failed" for t in self.tasks.values())

        if pending_tasks:
            task_list.status = "Processing"
        elif failed_tasks:
            task_list.status = "Failed"
        else:
            task_list.status = "Ready"

        try:
            await task_list.send()
            logger.debug(
                f"Sent updated Chainlit TaskList with status: {task_list.status}"
            )
        except Exception as e:
            logger.error(f"Failed to send Chainlit TaskList update: {e}", exc_info=True)
