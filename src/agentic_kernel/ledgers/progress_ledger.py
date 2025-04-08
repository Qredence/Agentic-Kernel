"""Ledger for tracking workflow progress."""

from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime

from ..types import WorkflowStep


class ProgressLedger:
    """Ledger for tracking workflow progress.

    Attributes:
        workflows: Dictionary mapping workflow IDs to workflow details
        step_status: Dictionary mapping step IDs to execution status
        dependencies: Dictionary mapping step IDs to dependency information
        progress_data: Dictionary mapping task IDs to progress data
    """

    def __init__(self):
        """Initialize the progress ledger."""
        self.workflows: Dict[str, List[WorkflowStep]] = {}
        self.step_status: Dict[str, str] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self.progress_data: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def register_workflow(self, workflow_id: str, steps: List[WorkflowStep]):
        """Register a new workflow.

        Args:
            workflow_id: ID for the workflow
            steps: List of workflow steps
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
            workflow_id: ID of the workflow
            step_name: Name of the step
            status: New status value
        """
        async with self._lock:
            step_id = f"{workflow_id}_{step_name}"
            self.step_status[step_id] = status

    def get_workflow_progress(self, workflow_id: str) -> Dict[str, Any]:
        """Get the progress of a workflow.

        Args:
            workflow_id: ID of the workflow

        Returns:
            Dictionary containing workflow progress information
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
            workflow_id: ID of the workflow

        Returns:
            List of step names that are ready to execute
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
            task_id: ID of the task
            progress_data: Progress data to record
        """
        async with self._lock:
            self.progress_data[task_id] = {
                "data": progress_data,
                "timestamp": datetime.now().isoformat(),
            }

    async def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get progress data for a task.

        Args:
            task_id: ID of the task

        Returns:
            Progress data if found, None otherwise
        """
        return self.progress_data.get(task_id)

    async def clear_progress(self, task_id: str):
        """Clear progress data for a task.

        Args:
            task_id: ID of the task
        """
        async with self._lock:
            self.progress_data.pop(task_id, None)

    def export_progress(self) -> str:
        """Export the progress data as JSON.

        Returns:
            JSON string containing progress data
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
            workflow_id: ID of the workflow

        Returns:
            Dictionary containing workflow metrics
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
