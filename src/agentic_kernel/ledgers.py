"""Ledger implementations for tracking tasks and progress in the agentic kernel."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class TaskEntry:
    """A single task entry in the task ledger."""
    id: str
    description: str
    assigned_agent: str
    created_at: datetime = field(default_factory=datetime.now)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressEntry:
    """A single progress entry in the progress ledger."""
    task_id: str
    status: str  # 'pending', 'in_progress', 'completed', 'failed'
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class TaskLedger:
    """Manages and tracks tasks in the workflow."""

    def __init__(self):
        """Initialize the task ledger."""
        self.tasks: Dict[str, TaskEntry] = {}
        self.task_counter = 0

    def add_task(
        self,
        description: str,
        assigned_agent: str,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a new task to the ledger.
        
        Args:
            description: Description of the task
            assigned_agent: Name of the agent assigned to the task
            dependencies: Optional list of task IDs this task depends on
            metadata: Optional additional task metadata
            
        Returns:
            The ID of the newly created task
        """
        self.task_counter += 1
        task_id = f"task_{self.task_counter}"
        
        self.tasks[task_id] = TaskEntry(
            id=task_id,
            description=description,
            assigned_agent=assigned_agent,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskEntry]:
        """Retrieve a task by its ID.
        
        Args:
            task_id: The ID of the task to retrieve
            
        Returns:
            The task entry if found, None otherwise
        """
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, **updates) -> bool:
        """Update a task's attributes.
        
        Args:
            task_id: The ID of the task to update
            **updates: Keyword arguments of attributes to update
            
        Returns:
            True if the task was updated, False if not found
        """
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        return True

    def get_dependent_tasks(self, task_id: str) -> List[TaskEntry]:
        """Get all tasks that depend on the given task.
        
        Args:
            task_id: The ID of the task to find dependents for
            
        Returns:
            List of task entries that depend on the given task
        """
        return [
            task for task in self.tasks.values()
            if task_id in task.dependencies
        ]

    def get_all_tasks(self) -> List[TaskEntry]:
        """Get all tasks in the ledger.
        
        Returns:
            List of all task entries
        """
        return list(self.tasks.values())


class ProgressLedger:
    """Tracks the progress and results of task execution."""

    def __init__(self):
        """Initialize the progress ledger."""
        self.entries: Dict[str, ProgressEntry] = {}

    def record_progress(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
        status: str = "in_progress",
        error: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record progress for a task.
        
        Args:
            task_id: The ID of the task to record progress for
            result: Optional result data from task execution
            status: Current status of the task
            error: Optional error message if task failed
            metrics: Optional metrics about task execution
        """
        now = datetime.now()
        
        if task_id not in self.entries:
            self.entries[task_id] = ProgressEntry(
                task_id=task_id,
                status=status,
                started_at=now,
                result=result,
                error=error,
                metrics=metrics or {}
            )
        else:
            entry = self.entries[task_id]
            entry.status = status
            if result:
                entry.result = result
            if error:
                entry.error = error
            if metrics:
                entry.metrics.update(metrics)
            if status in ["completed", "failed"]:
                entry.completed_at = now

    def get_progress(self, task_id: str) -> Optional[ProgressEntry]:
        """Get the progress entry for a task.
        
        Args:
            task_id: The ID of the task to get progress for
            
        Returns:
            The progress entry if found, None otherwise
        """
        return self.entries.get(task_id)

    def get_all_progress(self) -> List[ProgressEntry]:
        """Get all progress entries.
        
        Returns:
            List of all progress entries
        """
        return list(self.entries.values())

    def get_success_rate(self) -> float:
        """Calculate the success rate of completed tasks.
        
        Returns:
            Float between 0 and 1 representing the success rate
        """
        completed = sum(1 for entry in self.entries.values()
                       if entry.status == "completed")
        total = len(self.entries)
        return completed / total if total > 0 else 0.0

    def get_failed_tasks(self) -> List[ProgressEntry]:
        """Get all failed task entries.
        
        Returns:
            List of progress entries for failed tasks
        """
        return [
            entry for entry in self.entries.values()
            if entry.status == "failed"
        ]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all recorded metrics.
        
        Returns:
            Dictionary containing aggregated metrics
        """
        summary = {}
        for entry in self.entries.values():
            for metric_name, metric_value in entry.metrics.items():
                if isinstance(metric_value, (int, float)):
                    if metric_name not in summary:
                        summary[metric_name] = {
                            "total": 0,
                            "count": 0,
                            "min": metric_value,
                            "max": metric_value
                        }
                    summary[metric_name]["total"] += metric_value
                    summary[metric_name]["count"] += 1
                    summary[metric_name]["min"] = min(
                        summary[metric_name]["min"],
                        metric_value
                    )
                    summary[metric_name]["max"] = max(
                        summary[metric_name]["max"],
                        metric_value
                    )
        
        # Calculate averages
        for metric_data in summary.values():
            metric_data["average"] = (
                metric_data["total"] / metric_data["count"]
                if metric_data["count"] > 0
                else 0
            )
        
        return summary 