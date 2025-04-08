"""Type definitions for the Agentic-Kernel system.

This module defines the core data types used throughout the system, including:
1. Task and workflow related types
2. Configuration types
3. Status enums and constants
4. Base models for data validation

All types use Pydantic for validation and serialization.
"""

from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
import uuid
from pydantic import BaseModel, Field


# Task status literals
TaskStatus = Literal[
    "pending",  # Task is created but not started
    "running",  # Task is currently executing
    "completed",  # Task finished successfully
    "failed",  # Task encountered an error
    "cancelled",  # Task was manually cancelled
    "timeout",  # Task exceeded its time limit
]


class Task(BaseModel):
    """A task to be executed by an agent.

    This class represents a unit of work that can be executed by an agent in the system.
    Tasks have a lifecycle (pending -> running -> completed/failed) and can be retried
    on failure up to a maximum number of times.

    Attributes:
        id (str): Unique identifier for the task
        name (str): Human-readable name of the task
        description (Optional[str]): Detailed description of the task's purpose
        agent_type (str): Type of agent qualified to execute this task
        parameters (Dict[str, Any]): Configuration parameters for task execution
        status (TaskStatus): Current status in the task lifecycle
        max_retries (int): Maximum number of retry attempts on failure
        timeout (Optional[float]): Maximum execution time in seconds
        created_at (datetime): Timestamp when task was created
        updated_at (Optional[datetime]): Timestamp of last status update
        output (Optional[Dict[str, Any]]): Results from task execution
        error (Optional[str]): Error message if task failed
        retry_count (int): Number of times task has been retried

    Example:
        ```python
        task = Task(
            name="process_data",
            description="Process customer transaction data",
            agent_type="DataProcessor",
            parameters={"input_file": "transactions.csv"}
        )
        ```
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    agent_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = "pending"
    max_retries: int = 3
    timeout: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0


class WorkflowStep(BaseModel):
    """A step in a workflow.

    This class represents a single step in a workflow, which consists of a task
    and its execution requirements (dependencies, parallelization, conditions).

    Attributes:
        task (Task): The task to be executed in this step
        dependencies (List[str]): Names of tasks that must complete before this step
        parallel (bool): Whether this step can run in parallel with others
        condition (Optional[str]): Optional condition for step execution

    Example:
        ```python
        step = WorkflowStep(
            task=data_processing_task,
            dependencies=["fetch_data"],
            parallel=True
        )
        ```
    """

    task: Task
    dependencies: List[str] = Field(default_factory=list)
    parallel: bool = True
    condition: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
