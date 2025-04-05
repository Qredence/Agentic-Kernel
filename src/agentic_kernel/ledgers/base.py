from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from ..types import Task, WorkflowStep

class LedgerEntry(BaseModel):
    """Base class for entries in any ledger."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class PlanStep(BaseModel):
    """Represents a single step in the overall task plan."""
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    status: Literal['pending', 'in_progress', 'completed', 'failed'] = 'pending'
    depends_on: List[str] = Field(default_factory=list) # List of step_ids this step depends on

class TaskLedger(BaseModel):
    """Maintains the overall state and plan for a complex task."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    initial_facts: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    plan: List[PlanStep] = Field(default_factory=list)
    current_plan_version: int = 1
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    tasks: Dict[str, Task] = Field(default_factory=dict)
    task_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    def update_timestamp(self):
        self.last_updated = datetime.utcnow()

    async def add_task(self, task: Task) -> str:
        """Add a task to the ledger.
        
        Args:
            task: Task object to add
            
        Returns:
            Task ID
        """
        task_id = f"{task.name}_{datetime.utcnow().timestamp()}"
        self.tasks[task_id] = task
        self.update_timestamp()
        return task_id

    async def update_task_result(self, task_id: str, result: Dict[str, Any]):
        """Update the result of a task.
        
        Args:
            task_id: ID of the task
            result: Task execution result
        """
        self.task_results[task_id] = result
        self.update_timestamp()

class ProgressEntry(LedgerEntry):
    """Represents a single entry in the progress ledger for a specific plan step."""
    plan_step_id: str
    entry_type: Literal['reflection', 'delegation', 'agent_result', 'error', 'status_update']
    content: Dict[str, Any]
    agent_name: Optional[str] = None # Name of the agent involved, if applicable

class ProgressLedger(BaseModel):
    """Tracks the detailed step-by-step progress, reflections, and agent interactions for a task."""
    task_id: str
    entries: List[ProgressEntry] = Field(default_factory=list)
    current_status: Literal['not_started', 'running', 'stalled', 'completed', 'failed'] = 'not_started'
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    workflows: Dict[str, List[WorkflowStep]] = Field(default_factory=dict)
    step_status: Dict[str, str] = Field(default_factory=dict)

    def add_entry(self, entry: ProgressEntry):
        self.entries.append(entry)
        self.last_updated = datetime.utcnow()

    def update_status(self, status: Literal['not_started', 'running', 'stalled', 'completed', 'failed']):
        self.current_status = status
        self.last_updated = datetime.utcnow()

    async def register_workflow(self, workflow_id: str, steps: List[WorkflowStep]):
        """Register a new workflow.
        
        Args:
            workflow_id: ID for the workflow
            steps: List of workflow steps
        """
        self.workflows[workflow_id] = steps
        for step in steps:
            step_id = f"{workflow_id}_{step.task.name}"
            self.step_status[step_id] = "pending"

    async def update_step_status(self, workflow_id: str, step_name: str, status: str):
        """Update the status of a workflow step.
        
        Args:
            workflow_id: ID of the workflow
            step_name: Name of the step
            status: New status value
        """
        step_id = f"{workflow_id}_{step_name}"
        self.step_status[step_id] = status

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