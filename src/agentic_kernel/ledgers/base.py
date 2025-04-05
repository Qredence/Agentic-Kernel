from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

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

    def update_timestamp(self):
        self.last_updated = datetime.utcnow()

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

    def add_entry(self, entry: ProgressEntry):
        self.entries.append(entry)
        self.last_updated = datetime.utcnow()

    def update_status(self, status: Literal['not_started', 'running', 'stalled', 'completed', 'failed']):
        self.current_status = status
        self.last_updated = datetime.utcnow() 