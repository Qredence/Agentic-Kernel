"""Type definitions for the Agentic-Kernel system."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class Task(BaseModel):
    """A task to be executed by an agent.
    
    Attributes:
        name: The name of the task
        description: A description of what the task should do
        agent_type: The type of agent that should execute this task
        parameters: Parameters needed for task execution
        max_retries: Maximum number of retry attempts
        timeout: Maximum time in seconds for task execution
    """

    name: str
    description: str
    agent_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    max_retries: int = 3
    timeout: Optional[float] = None


class WorkflowStep(BaseModel):
    """A step in a workflow.
    
    Attributes:
        task: The task to be executed in this step
        dependencies: Names of tasks that must complete before this step
        parallel: Whether this step can run in parallel with others
        condition: Optional condition for step execution
    """

    task: Task
    dependencies: List[str] = Field(default_factory=list)
    parallel: bool = True
    condition: Optional[str] = None

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True 