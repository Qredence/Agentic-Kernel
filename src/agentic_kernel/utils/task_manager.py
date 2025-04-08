"""Task management utilities."""

import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List

from ..types import Task
from ..ledgers.task_ledger import TaskLedger
from ..ledgers.progress_ledger import ProgressLedger

# Try importing Chainlit, but allow tests to run without it
try:
    import chainlit as cl

    CHAINLIT_AVAILABLE = True
except ImportError:
    CHAINLIT_AVAILABLE = False
    cl = None

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages task creation, assignment, and tracking, including Chainlit UI sync."""

    def __init__(
        self, task_ledger: TaskLedger, progress_ledger: ProgressLedger
    ) -> None:
        """Initialize the TaskManager.

        Args:
            task_ledger: The task ledger to use for task tracking.
            progress_ledger: The progress ledger to use for progress tracking.
        """
        self.task_ledger = task_ledger
        self.progress_ledger = progress_ledger
        self.tasks: Dict[str, Task] = {}
        self.message_task_map: Dict[str, str] = (
            {}
        )  # Maps Chainlit message IDs to task IDs
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
            name: Name of the task
            agent_type: Type of agent to execute the task
            description: Optional description of the task
            parameters: Optional parameters for task execution
            max_retries: Maximum number of retry attempts
            timeout: Maximum time in seconds for execution

        Returns:
            The created task
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
            task_id: ID of the task

        Returns:
            The task if found, None otherwise
        """
        return await self.task_ledger.get_task(task_id)

    async def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        """List tasks, optionally filtered by status.

        Args:
            status: Optional status to filter by

        Returns:
            List of matching tasks
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
            task_id: ID of the task
            status: New status value
            result: Optional result data
            progress: Optional progress data
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
            task_id: ID of the task
            result: Optional result data
            metrics: Optional metrics data
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
            task_id: ID of the task
            error: Error message
            metrics: Optional metrics data
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
            task_id: ID of the task
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
            task_id: ID of the task

        Returns:
            Progress data if found, None otherwise
        """
        return await self.progress_ledger.get_progress(task_id)

    async def link_message_to_task(self, message_id: str, task_id: str) -> None:
        """Link a Chainlit message ID to a task ID for tracking purposes.

        Args:
            message_id: The ID of the Chainlit message.
            task_id: The ID of the task associated with the message.
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
                cl_status = (
                    cl.TaskStatus.RUNNING
                )  # Default to running if not explicitly ended

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
