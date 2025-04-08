"""Workflow versioning and history management for the orchestrator.

This module provides functionality to track workflow versions and execution history.
It enables version control for workflows, allowing comparison, rollback, and auditing.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from ..types import Task, WorkflowStep

logger = logging.getLogger(__name__)


class WorkflowVersion:
    """Represents a specific version of a workflow.
    
    Tracks metadata about a workflow version including its steps, creation time,
    author, and description of changes.
    
    Attributes:
        workflow_id: The workflow's unique identifier
        version_id: The version's unique identifier
        steps: The workflow steps in this version
        created_at: When this version was created
        created_by: Who created this version (user or agent)
        parent_version_id: ID of the version this was derived from (if any)
        description: Description of changes in this version
        metadata: Additional metadata for this version
    """
    
    def __init__(
        self,
        workflow_id: str,
        steps: List[WorkflowStep],
        created_by: str,
        parent_version_id: Optional[str] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a workflow version.
        
        Args:
            workflow_id: The workflow's unique identifier
            steps: The workflow steps in this version
            created_by: Who created this version (user or agent)
            parent_version_id: ID of the version this was derived from
            description: Description of changes in this version
            metadata: Additional metadata for this version
        """
        self.workflow_id = workflow_id
        self.version_id = str(uuid4())
        self.steps = steps
        self.created_at = datetime.utcnow()
        self.created_by = created_by
        self.parent_version_id = parent_version_id
        self.description = description
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the workflow version to a dictionary.
        
        Returns:
            Dictionary representation of this workflow version
        """
        return {
            "workflow_id": self.workflow_id,
            "version_id": self.version_id,
            "steps": [self._step_to_dict(step) for step in self.steps],
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "parent_version_id": self.parent_version_id,
            "description": self.description,
            "metadata": self.metadata,
        }
        
    @staticmethod
    def _step_to_dict(step: WorkflowStep) -> Dict[str, Any]:
        """Convert a workflow step to a dictionary.
        
        Args:
            step: The workflow step to convert
            
        Returns:
            Dictionary representation of the workflow step
        """
        return {
            "task": {
                "id": step.task.id,
                "name": step.task.name,
                "description": step.task.description,
                "agent_type": step.task.agent_type,
                "parameters": step.task.parameters,
                "status": step.task.status,
                "max_retries": step.task.max_retries,
                "timeout": step.task.timeout,
            },
            "dependencies": step.dependencies,
            "parallel": step.parallel,
            "condition": step.condition,
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowVersion":
        """Create a workflow version from a dictionary.
        
        Args:
            data: Dictionary representation of a workflow version
            
        Returns:
            Instantiated workflow version
        """
        steps = [cls._dict_to_step(step_data) for step_data in data["steps"]]
        version = cls(
            workflow_id=data["workflow_id"],
            steps=steps,
            created_by=data["created_by"],
            parent_version_id=data.get("parent_version_id"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )
        version.version_id = data["version_id"]
        version.created_at = datetime.fromisoformat(data["created_at"])
        return version
        
    @staticmethod
    def _dict_to_step(data: Dict[str, Any]) -> WorkflowStep:
        """Convert a dictionary to a workflow step.
        
        Args:
            data: Dictionary representation of a workflow step
            
        Returns:
            Instantiated workflow step
        """
        task_data = data["task"]
        task = Task(
            id=task_data["id"],
            name=task_data["name"],
            description=task_data.get("description"),
            agent_type=task_data["agent_type"],
            parameters=task_data.get("parameters", {}),
            status=task_data.get("status", "pending"),
            max_retries=task_data.get("max_retries", 3),
            timeout=task_data.get("timeout"),
        )
        return WorkflowStep(
            task=task,
            dependencies=data.get("dependencies", []),
            parallel=data.get("parallel", True),
            condition=data.get("condition"),
        )


class ExecutionRecord:
    """Records a single execution of a workflow version.
    
    Tracks metadata about workflow execution including start/end time,
    execution results, and performance metrics.
    
    Attributes:
        execution_id: Unique ID for this execution
        workflow_id: ID of the workflow
        version_id: ID of the workflow version that was executed
        start_time: When execution started
        end_time: When execution completed
        status: Overall execution status
        step_results: Results for each executed step
        metrics: Performance metrics for this execution
        errors: Any errors encountered during execution
    """
    
    def __init__(
        self,
        workflow_id: str,
        version_id: str,
    ):
        """Initialize an execution record.
        
        Args:
            workflow_id: ID of the workflow
            version_id: ID of the workflow version
        """
        self.execution_id = str(uuid4())
        self.workflow_id = workflow_id
        self.version_id = version_id
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.status = "running"
        self.step_results: Dict[str, Dict[str, Any]] = {}
        self.metrics: Dict[str, Any] = {
            "execution_time": 0.0,
            "resource_usage": {},
            "success_rate": 0.0,
            "replanning_count": 0,
        }
        self.errors: List[Dict[str, Any]] = []
        
    def add_step_result(self, step_name: str, result: Dict[str, Any]) -> None:
        """Add a step execution result.
        
        Args:
            step_name: Name of the executed step
            result: Result of step execution
        """
        self.step_results[step_name] = result
        
        # Update metrics based on step result
        if "metrics" in result:
            for key, value in result["metrics"].items():
                if key not in self.metrics["resource_usage"]:
                    self.metrics["resource_usage"][key] = 0
                self.metrics["resource_usage"][key] += value
                
        # Record error if step failed
        if result.get("status") != "success":
            self.errors.append({
                "step": step_name,
                "error": result.get("error", "Unknown error"),
                "time": datetime.utcnow().isoformat(),
            })
            
    def complete(self, status: str) -> None:
        """Mark execution as complete.
        
        Args:
            status: Final execution status
        """
        self.end_time = datetime.utcnow()
        self.status = status
        
        # Calculate final metrics
        if self.start_time and self.end_time:
            self.metrics["execution_time"] = (self.end_time - self.start_time).total_seconds()
            
        # Calculate success rate
        total_steps = len(self.step_results)
        if total_steps > 0:
            successful_steps = sum(
                1 for result in self.step_results.values()
                if result.get("status") == "success"
            )
            self.metrics["success_rate"] = successful_steps / total_steps
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert the execution record to a dictionary.
        
        Returns:
            Dictionary representation of this execution record
        """
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "version_id": self.version_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "step_results": self.step_results,
            "metrics": self.metrics,
            "errors": self.errors,
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionRecord":
        """Create an execution record from a dictionary.
        
        Args:
            data: Dictionary representation of an execution record
            
        Returns:
            Instantiated execution record
        """
        record = cls(
            workflow_id=data["workflow_id"],
            version_id=data["version_id"],
        )
        record.execution_id = data["execution_id"]
        record.start_time = datetime.fromisoformat(data["start_time"])
        if data["end_time"]:
            record.end_time = datetime.fromisoformat(data["end_time"])
        record.status = data["status"]
        record.step_results = data["step_results"]
        record.metrics = data["metrics"]
        record.errors = data["errors"]
        return record


class WorkflowHistory:
    """Manages workflow version history and execution records.
    
    Provides methods to create, retrieve, and manage workflow versions
    and their execution history.
    
    Attributes:
        workflows: Dictionary mapping workflow IDs to metadata
        versions: Dictionary mapping workflow IDs to lists of versions
        executions: Dictionary mapping workflow IDs to lists of executions
    """
    
    def __init__(self):
        """Initialize the workflow history manager."""
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.versions: Dict[str, List[WorkflowVersion]] = {}
        self.executions: Dict[str, List[ExecutionRecord]] = {}
        
    async def create_workflow(
        self,
        name: str,
        description: str,
        creator: str,
        steps: List[WorkflowStep],
        tags: Optional[List[str]] = None,
    ) -> Tuple[str, str]:
        """Create a new workflow with initial version.
        
        Args:
            name: Name of the workflow
            description: Description of the workflow
            creator: Who created the workflow
            steps: Initial workflow steps
            tags: Optional tags for categorizing the workflow
            
        Returns:
            Tuple of (workflow_id, version_id)
        """
        workflow_id = str(uuid4())
        
        # Create workflow metadata
        self.workflows[workflow_id] = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": creator,
            "tags": tags or [],
            "current_version_id": None,
        }
        
        # Create initial version
        version = await self.create_version(
            workflow_id=workflow_id,
            steps=steps,
            created_by=creator,
            description="Initial version",
        )
        
        # Set as current version
        self.workflows[workflow_id]["current_version_id"] = version.version_id
        
        return workflow_id, version.version_id
        
    async def create_version(
        self,
        workflow_id: str,
        steps: List[WorkflowStep],
        created_by: str,
        parent_version_id: Optional[str] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        set_as_current: bool = True,
    ) -> WorkflowVersion:
        """Create a new version of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            steps: Steps for this version
            created_by: Who created this version
            parent_version_id: ID of the parent version
            description: Description of changes
            metadata: Additional metadata
            set_as_current: Whether to set this as the current version
            
        Returns:
            The created workflow version
        """
        # Initialize versions list if needed
        if workflow_id not in self.versions:
            self.versions[workflow_id] = []
            
        # If parent_version_id not specified, use current version
        if not parent_version_id and workflow_id in self.workflows:
            parent_version_id = self.workflows[workflow_id].get("current_version_id")
            
        # Create new version
        version = WorkflowVersion(
            workflow_id=workflow_id,
            steps=steps,
            created_by=created_by,
            parent_version_id=parent_version_id,
            description=description,
            metadata=metadata,
        )
        
        # Add to versions list
        self.versions[workflow_id].append(version)
        
        # Update current version if requested
        if set_as_current and workflow_id in self.workflows:
            self.workflows[workflow_id]["current_version_id"] = version.version_id
            
        logger.info(
            f"Created workflow version {version.version_id} for workflow {workflow_id}"
        )
        
        return version
        
    async def get_version(
        self, workflow_id: str, version_id: Optional[str] = None
    ) -> Optional[WorkflowVersion]:
        """Get a specific workflow version.
        
        Args:
            workflow_id: ID of the workflow
            version_id: ID of the version (or None for current version)
            
        Returns:
            The workflow version, or None if not found
        """
        # Get current version ID if none specified
        if not version_id and workflow_id in self.workflows:
            version_id = self.workflows[workflow_id].get("current_version_id")
            
        if not version_id:
            return None
            
        # Find the version
        if workflow_id in self.versions:
            for version in self.versions[workflow_id]:
                if version.version_id == version_id:
                    return version
                    
        return None
        
    async def get_version_history(
        self, workflow_id: str
    ) -> List[Dict[str, Any]]:
        """Get the version history for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            List of version metadata in chronological order
        """
        if workflow_id not in self.versions:
            return []
            
        # Create a chronological history with parent-child relationships
        versions = sorted(
            self.versions[workflow_id],
            key=lambda v: v.created_at
        )
        
        return [
            {
                "version_id": v.version_id,
                "created_at": v.created_at.isoformat(),
                "created_by": v.created_by,
                "description": v.description,
                "parent_version_id": v.parent_version_id,
                "is_current": v.version_id == self.workflows[workflow_id].get("current_version_id"),
            }
            for v in versions
        ]
        
    async def set_current_version(
        self, workflow_id: str, version_id: str
    ) -> bool:
        """Set the current version of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            version_id: ID of the version to set as current
            
        Returns:
            True if successful, False otherwise
        """
        # Verify workflow exists
        if workflow_id not in self.workflows:
            logger.error(f"Workflow {workflow_id} not found")
            return False
            
        # Verify version exists
        version_exists = False
        if workflow_id in self.versions:
            for version in self.versions[workflow_id]:
                if version.version_id == version_id:
                    version_exists = True
                    break
                    
        if not version_exists:
            logger.error(f"Version {version_id} not found for workflow {workflow_id}")
            return False
            
        # Update current version
        self.workflows[workflow_id]["current_version_id"] = version_id
        logger.info(f"Set current version to {version_id} for workflow {workflow_id}")
        return True
        
    async def compare_versions(
        self, workflow_id: str, version_id1: str, version_id2: str
    ) -> Dict[str, Any]:
        """Compare two versions of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            version_id1: ID of the first version
            version_id2: ID of the second version
            
        Returns:
            Comparison results detailing differences
        """
        # Get the versions
        version1 = await self.get_version(workflow_id, version_id1)
        version2 = await self.get_version(workflow_id, version_id2)
        
        if not version1 or not version2:
            missing = "first" if not version1 else "second"
            logger.error(f"Cannot compare versions: {missing} version not found")
            return {"error": f"Cannot compare versions: {missing} version not found"}
            
        # Compare versions
        added_steps = []
        removed_steps = []
        modified_steps = []
        
        # Map steps by name for easy comparison
        steps1 = {step.task.name: step for step in version1.steps}
        steps2 = {step.task.name: step for step in version2.steps}
        
        # Find added and modified steps
        for name, step in steps2.items():
            if name not in steps1:
                added_steps.append(name)
            elif not self._steps_equal(step, steps1[name]):
                modified_steps.append(name)
                
        # Find removed steps
        for name in steps1:
            if name not in steps2:
                removed_steps.append(name)
                
        # Build comparison result
        return {
            "workflow_id": workflow_id,
            "version1": {
                "id": version_id1,
                "created_at": version1.created_at.isoformat(),
                "created_by": version1.created_by,
            },
            "version2": {
                "id": version_id2,
                "created_at": version2.created_at.isoformat(),
                "created_by": version2.created_by,
            },
            "differences": {
                "added_steps": added_steps,
                "removed_steps": removed_steps,
                "modified_steps": modified_steps,
                "total_changes": len(added_steps) + len(removed_steps) + len(modified_steps),
            },
        }
        
    def _steps_equal(self, step1: WorkflowStep, step2: WorkflowStep) -> bool:
        """Compare two workflow steps for equality.
        
        Args:
            step1: First workflow step
            step2: Second workflow step
            
        Returns:
            True if steps are functionally equivalent
        """
        # Compare basic properties
        if step1.dependencies != step2.dependencies:
            return False
        if step1.parallel != step2.parallel:
            return False
        if step1.condition != step2.condition:
            return False
            
        # Compare tasks (excluding runtime states)
        task1, task2 = step1.task, step2.task
        
        if task1.name != task2.name:
            return False
        if task1.description != task2.description:
            return False
        if task1.agent_type != task2.agent_type:
            return False
        if task1.parameters != task2.parameters:
            return False
        if task1.max_retries != task2.max_retries:
            return False
        if task1.timeout != task2.timeout:
            return False
            
        return True
        
    async def start_execution(
        self, workflow_id: str, version_id: Optional[str] = None
    ) -> ExecutionRecord:
        """Start a new workflow execution record.
        
        Args:
            workflow_id: ID of the workflow
            version_id: ID of the version to execute (None for current)
            
        Returns:
            The created execution record
        """
        # Get version ID if not specified
        if not version_id and workflow_id in self.workflows:
            version_id = self.workflows[workflow_id].get("current_version_id")
            
        if not version_id:
            raise ValueError(f"No version specified for workflow {workflow_id}")
            
        # Initialize executions list if needed
        if workflow_id not in self.executions:
            self.executions[workflow_id] = []
            
        # Create execution record
        execution = ExecutionRecord(
            workflow_id=workflow_id,
            version_id=version_id,
        )
        
        # Add to executions list
        self.executions[workflow_id].append(execution)
        
        logger.info(
            f"Started execution {execution.execution_id} for workflow version {version_id}"
        )
        
        return execution
        
    async def record_step_result(
        self,
        execution_id: str,
        step_name: str,
        result: Dict[str, Any],
    ) -> None:
        """Record a step execution result.
        
        Args:
            execution_id: ID of the execution
            step_name: Name of the executed step
            result: Result of step execution
        """
        # Find execution record
        execution = None
        for workflow_id, executions in self.executions.items():
            for record in executions:
                if record.execution_id == execution_id:
                    execution = record
                    break
            if execution:
                break
                
        if not execution:
            logger.error(f"Execution record {execution_id} not found")
            return
            
        # Add step result
        execution.add_step_result(step_name, result)
        logger.debug(f"Recorded result for step {step_name} in execution {execution_id}")
        
    async def complete_execution(
        self, execution_id: str, status: str
    ) -> Optional[ExecutionRecord]:
        """Mark an execution as complete.
        
        Args:
            execution_id: ID of the execution
            status: Final execution status
            
        Returns:
            The updated execution record, or None if not found
        """
        # Find execution record
        execution = None
        for workflow_id, executions in self.executions.items():
            for record in executions:
                if record.execution_id == execution_id:
                    execution = record
                    break
            if execution:
                break
                
        if not execution:
            logger.error(f"Execution record {execution_id} not found")
            return None
            
        # Mark as complete
        execution.complete(status)
        logger.info(f"Completed execution {execution_id} with status {status}")
        
        return execution
        
    async def get_execution_history(
        self, workflow_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get execution history for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            limit: Maximum number of records to return
            
        Returns:
            List of execution records in reverse chronological order
        """
        if workflow_id not in self.executions:
            return []
            
        # Sort by start time (most recent first)
        executions = sorted(
            self.executions[workflow_id],
            key=lambda e: e.start_time,
            reverse=True
        )
        
        # Limit number of records
        executions = executions[:limit]
        
        return [
            {
                "execution_id": e.execution_id,
                "version_id": e.version_id,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat() if e.end_time else None,
                "status": e.status,
                "metrics": {
                    "execution_time": e.metrics.get("execution_time", 0),
                    "success_rate": e.metrics.get("success_rate", 0),
                },
                "error_count": len(e.errors),
            }
            for e in executions
        ]
        
    async def get_execution_details(
        self, execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a workflow execution.
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            Detailed execution record, or None if not found
        """
        # Find execution record
        for workflow_id, executions in self.executions.items():
            for record in executions:
                if record.execution_id == execution_id:
                    return record.to_dict()
                    
        return None
        
    async def persist_history(self, storage_path: str) -> None:
        """Persist workflow history to storage.
        
        Args:
            storage_path: Path to storage directory
        """
        data = {
            "workflows": self.workflows,
            "versions": {
                wid: [v.to_dict() for v in versions]
                for wid, versions in self.versions.items()
            },
            "executions": {
                wid: [e.to_dict() for e in executions]
                for wid, executions in self.executions.items()
            },
        }
        
        with open(storage_path, "w") as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Persisted workflow history to {storage_path}")
        
    @classmethod
    async def load_history(cls, storage_path: str) -> "WorkflowHistory":
        """Load workflow history from storage.
        
        Args:
            storage_path: Path to storage file
            
        Returns:
            Loaded WorkflowHistory instance
        """
        history = cls()
        
        try:
            with open(storage_path, "r") as f:
                data = json.load(f)
                
            # Load workflows
            history.workflows = data.get("workflows", {})
            
            # Load versions
            for wid, version_dicts in data.get("versions", {}).items():
                history.versions[wid] = [
                    WorkflowVersion.from_dict(v) for v in version_dicts
                ]
                
            # Load executions
            for wid, execution_dicts in data.get("executions", {}).items():
                history.executions[wid] = [
                    ExecutionRecord.from_dict(e) for e in execution_dicts
                ]
                
            logger.info(f"Loaded workflow history from {storage_path}")
            
        except Exception as e:
            logger.error(f"Error loading workflow history: {str(e)}")
            
        return history 