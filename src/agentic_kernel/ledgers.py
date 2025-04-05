"""Ledger implementations for tracking tasks and progress."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import json

from .types import Task, WorkflowStep


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
            task_id = f"{task.name}_{datetime.now().timestamp()}"
            self.tasks[task_id] = task
            return task_id

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
            "metrics": self.task_metrics.get(task_id)
        }

    def export_ledger(self) -> str:
        """Export the ledger data as JSON.
        
        Returns:
            JSON string containing ledger data
        """
        data = {
            "tasks": {k: v.dict() for k, v in self.tasks.items()},
            "results": self.task_results,
            "metrics": self.task_metrics
        }
        return json.dumps(data, indent=2)


class ProgressLedger:
    """Ledger for tracking workflow progress.
    
    Attributes:
        workflows: Dictionary mapping workflow IDs to workflow details
        step_status: Dictionary mapping step IDs to execution status
        dependencies: Dictionary mapping step IDs to dependency information
    """

    def __init__(self):
        """Initialize the progress ledger."""
        self.workflows: Dict[str, List[WorkflowStep]] = {}
        self.step_status: Dict[str, str] = {}
        self.dependencies: Dict[str, List[str]] = {}
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
                "dependencies": self.dependencies.get(step_id, [])
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