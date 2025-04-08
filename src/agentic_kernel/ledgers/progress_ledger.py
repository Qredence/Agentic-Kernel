"""Ledger for tracking workflow progress.

This module provides a ledger implementation for tracking workflow execution
progress, step dependencies, and status updates. It supports concurrent access
through asyncio locks and provides comprehensive workflow monitoring capabilities.

Key features:
    1. Workflow registration and tracking
    2. Step dependency management
    3. Progress monitoring and metrics
    4. Concurrent access support
    5. Progress data export capabilities

Example:
    .. code-block:: python

        # Create a progress ledger
        ledger = ProgressLedger()

        # Register a workflow
        steps = [
            WorkflowStep(task=Task(name="step1"), dependencies=[]),
            WorkflowStep(task=Task(name="step2"), dependencies=["step1"])
        ]
        await ledger.register_workflow("workflow_123", steps)

        # Update step status
        await ledger.update_step_status("workflow_123", "step1", "completed")

        # Get ready steps
        ready_steps = ledger.get_ready_steps("workflow_123")
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..types import WorkflowStep


class ProgressLedger:
    """Ledger for tracking workflow progress.

    This class provides a thread-safe implementation for tracking workflow
    execution progress, managing step dependencies, and collecting progress
    metrics. It supports concurrent access through asyncio locks and provides
    comprehensive workflow monitoring capabilities.

    Attributes:
        workflows (Dict[str, List[WorkflowStep]]): Dictionary mapping workflow IDs to workflow steps.
        step_status (Dict[str, str]): Dictionary mapping step IDs to execution status.
        dependencies (Dict[str, List[str]]): Dictionary mapping step IDs to dependency information.
        progress_data (Dict[str, Dict[str, Any]]): Dictionary mapping task IDs to progress data.

    Example:
        .. code-block:: python

            # Initialize ledger
            ledger = ProgressLedger()

            # Create workflow steps
            steps = [
                WorkflowStep(
                    task=Task(name="fetch_data"),
                    dependencies=[]
                ),
                WorkflowStep(
                    task=Task(name="process_data"),
                    dependencies=["fetch_data"]
                )
            ]

            # Register workflow and track progress
            await ledger.register_workflow("workflow_123", steps)
            await ledger.update_step_status(
                "workflow_123",
                "fetch_data",
                "completed"
            )
    """

    def __init__(self):
        """Initialize the progress ledger.

        Creates empty dictionaries for workflows, step status, dependencies,
        and progress data, and initializes the asyncio lock for thread-safe
        operations.
        """
        self.workflows: Dict[str, List[WorkflowStep]] = {}
        self.step_status: Dict[str, str] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self.progress_data: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def register_workflow(self, workflow_id: str, steps: List[WorkflowStep]):
        """Register a new workflow.

        Args:
            workflow_id: ID for the workflow.
            steps: List of workflow steps.

        Example:
            .. code-block:: python

                steps = [
                    WorkflowStep(task=Task(name="step1"), dependencies=[]),
                    WorkflowStep(task=Task(name="step2"), dependencies=["step1"])
                ]
                await ledger.register_workflow("workflow_123", steps)
        """
        async with self._lock:
            self.workflows[workflow_id] = steps
            for step in steps:
                step_id = f"{workflow_id}_{step.task.name}"
                self.step_status[step_id] = "pending"
                self.dependencies[step_id] = step.dependencies

    async def update_step_status(self, workflow_id: str, step_name: str, status: str):
        """Update the status of a workflow step.

        Args:
            workflow_id: ID of the workflow.
            step_name: Name of the step.
            status: New status value.

        Example:
            .. code-block:: python

                await ledger.update_step_status(
                    "workflow_123",
                    "process_data",
                    "completed"
                )
        """
        async with self._lock:
            step_id = f"{workflow_id}_{step_name}"
            self.step_status[step_id] = status

    def get_workflow_progress(self, workflow_id: str) -> Dict[str, Any]:
        """Get the progress of a workflow.

        Args:
            workflow_id: ID of the workflow.

        Returns:
            Dict[str, Any]: Dictionary containing workflow progress information.

        Example:
            .. code-block:: python

                progress = ledger.get_workflow_progress("workflow_123")
                for step_name, details in progress.items():
                    print(f"Step: {step_name}")
                    print(f"Status: {details['status']}")
                    print(f"Dependencies: {details['dependencies']}")
        """
        steps = self.workflows.get(workflow_id, [])
        progress = {}
        for step in steps:
            step_id = f"{workflow_id}_{step.task.name}"
            progress[step.task.name] = {
                "status": self.step_status.get(step_id, "unknown"),
                "dependencies": self.dependencies.get(step_id, []),
            }
        return progress

    def get_ready_steps(self, workflow_id: str) -> List[str]:
        """Get steps that are ready to execute.

        Args:
            workflow_id: ID of the workflow.

        Returns:
            List[str]: List of step names that are ready to execute.

        Example:
            .. code-block:: python

                ready_steps = ledger.get_ready_steps("workflow_123")
                for step in ready_steps:
                    print(f"Ready to execute: {step}")
        """
        ready_steps = []
        for step in self.workflows.get(workflow_id, []):
            step_id = f"{workflow_id}_{step.task.name}"
            if self.step_status.get(step_id) == "pending":
                deps_completed = all(
                    self.step_status.get(f"{workflow_id}_{dep}", "") == "completed"
                    for dep in step.dependencies
                )
                if deps_completed:
                    ready_steps.append(step.task.name)
        return ready_steps

    async def record_progress(self, task_id: str, progress_data: Dict[str, Any]):
        """Record progress data for a task.

        Args:
            task_id: ID of the task.
            progress_data: Progress data to record.

        Example:
            .. code-block:: python

                await ledger.record_progress(
                    "task_123",
                    {
                        "percent_complete": 75,
                        "current_stage": "processing",
                        "items_processed": 150
                    }
                )
        """
        async with self._lock:
            self.progress_data[task_id] = {
                "data": progress_data,
                "timestamp": datetime.now().isoformat(),
            }

    async def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get progress data for a task.

        Args:
            task_id: ID of the task.

        Returns:
            Optional[Dict[str, Any]]: Progress data if found, None otherwise.

        Example:
            .. code-block:: python

                progress = await ledger.get_progress("task_123")
                if progress:
                    print(f"Progress: {progress['data']}")
                    print(f"Last updated: {progress['timestamp']}")
        """
        return self.progress_data.get(task_id)

    async def clear_progress(self, task_id: str):
        """Clear progress data for a task.

        Args:
            task_id: ID of the task.

        Example:
            .. code-block:: python

                await ledger.clear_progress("task_123")
        """
        async with self._lock:
            self.progress_data.pop(task_id, None)

    def export_progress(self) -> str:
        """Export the progress data as JSON.

        Returns:
            str: JSON string containing progress data.

        Example:
            .. code-block:: python

                json_data = ledger.export_progress()
                with open("progress_backup.json", "w") as f:
                    f.write(json_data)
        """
        data = {
            "workflows": {
                k: [step.dict() for step in v] for k, v in self.workflows.items()
            },
            "step_status": self.step_status,
            "dependencies": self.dependencies,
            "progress_data": self.progress_data,
        }
        return json.dumps(data, indent=2)

    async def get_workflow_metrics(self, workflow_id: str) -> Dict[str, Any]:
        """Get metrics for a workflow.

        Args:
            workflow_id: ID of the workflow.

        Returns:
            Dict[str, Any]: Dictionary containing workflow metrics.

        Example:
            .. code-block:: python

                metrics = await ledger.get_workflow_metrics("workflow_123")
                print(f"Total steps: {metrics['total_steps']}")
                print(f"Completed: {metrics['completed_steps']}")
                print(f"Progress: {metrics['progress_percentage']}%")
        """
        steps = self.workflows.get(workflow_id, [])
        if not steps:
            return {}

        total_steps = len(steps)
        completed_steps = sum(
            1
            for step in steps
            if self.step_status.get(f"{workflow_id}_{step.task.name}") == "completed"
        )
        failed_steps = sum(
            1
            for step in steps
            if self.step_status.get(f"{workflow_id}_{step.task.name}") == "failed"
        )

        return {
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "progress_percentage": (
                (completed_steps / total_steps) * 100 if total_steps > 0 else 0
            ),
        }
