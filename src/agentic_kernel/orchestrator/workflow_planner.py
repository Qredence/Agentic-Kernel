"""Workflow planning functionality for the orchestrator.

This module provides the WorkflowPlanner class, which is responsible for
creating workflows, planning and replanning workflows, and managing workflow versions.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from ..types import WorkflowStep
from .workflow_history import WorkflowHistory
from .workflow_optimizer import WorkflowOptimizer

logger = logging.getLogger(__name__)


class WorkflowPlanner:
    """Plans and replans workflows.

    This class is responsible for:
    1. Creating new workflows
    2. Replanning workflows when steps fail
    3. Creating replanning context
    4. Managing workflow versions

    Attributes:
        workflow_history: Component for tracking workflow versions and execution history
        workflow_optimizer: Component for optimizing workflows
        max_planning_attempts: Maximum number of planning attempts
    """

    def __init__(
        self,
        workflow_history: WorkflowHistory,
        workflow_optimizer: WorkflowOptimizer | None = None,
    ):
        """Initialize the workflow planner.

        Args:
            workflow_history: Component for tracking workflow versions and execution history
            workflow_optimizer: Optional component for optimizing workflows
        """
        self.workflow_history = workflow_history
        self.workflow_optimizer = workflow_optimizer or WorkflowOptimizer()
        self.max_planning_attempts = 3

    async def create_workflow(
        self,
        name: str,
        description: str,
        steps: list[WorkflowStep],
        creator: str = "system",
        tags: list[str] | None = None,
    ) -> str:
        """Create a new workflow and track its initial version.

        Args:
            name: Name of the workflow
            description: Description of the workflow's purpose
            steps: List of workflow steps
            creator: Who created the workflow
            tags: Optional tags for categorizing the workflow

        Returns:
            ID of the created workflow
        """
        # Generate a workflow ID
        workflow_id = str(uuid.uuid4())

        # Create the initial version
        await self.workflow_history.create_version(
            workflow_id=workflow_id,
            steps=steps,
            created_by=creator,
            description=f"Initial version of {name}",
            tags=tags,
        )

        # Store workflow metadata
        await self.workflow_history.store_workflow_metadata(
            workflow_id=workflow_id,
            name=name,
            description=description,
            creator=creator,
            created_at=datetime.now(),
            tags=tags or [],
        )

        logger.info(f"Created workflow: {name} ({workflow_id}) with {len(steps)} steps")
        return workflow_id

    async def replan_workflow(
        self,
        workflow_id: str,
        version_id: str | None = None,
        completed_steps: list[str] = None,
        failed_steps: list[str] = None,
        context: dict[str, Any] | None = None,
    ) -> str | None:
        """Replan a workflow based on execution results.

        Args:
            workflow_id: ID of the workflow to replan
            version_id: Optional version ID (uses current version if not specified)
            completed_steps: List of completed step names
            failed_steps: List of failed step names
            context: Optional additional context for replanning

        Returns:
            ID of the new version, or None if replanning failed
        """
        # Get the current version
        version = await self.workflow_history.get_version(workflow_id, version_id)
        if not version:
            logger.error(f"Cannot replan: version not found for workflow {workflow_id}")
            return None

        # Create replanning context
        replanning_context = self._create_replanning_context(
            version.steps, completed_steps or [], failed_steps or [], context or {},
        )

        try:
            # Get workflow metadata
            metadata = await self.workflow_history.get_workflow_metadata(workflow_id)
            if not metadata:
                logger.error(f"Cannot replan: metadata not found for workflow {workflow_id}")
                return None

            # Create a new plan based on the current state
            # In a real implementation, this might involve an LLM or other planning system
            # For now, we'll just create a simplified plan that skips the failed steps
            new_steps = []
            for step in version.steps:
                # Include completed steps as-is
                if step.task.name in (completed_steps or []):
                    new_steps.append(step)
                    continue

                # Skip failed steps
                if step.task.name in (failed_steps or []):
                    continue

                # For steps that depend on failed steps, update dependencies
                updated_dependencies = [
                    dep for dep in step.dependencies if dep not in (failed_steps or [])
                ]
                
                # Create a new step with updated dependencies
                new_step = WorkflowStep(
                    task=step.task,
                    dependencies=updated_dependencies,
                    parallel=step.parallel,
                    condition=step.condition,
                )
                new_steps.append(new_step)

            # Create a new version with the updated steps
            new_version_id = await self.workflow_history.create_version(
                workflow_id=workflow_id,
                steps=new_steps,
                created_by="workflow_planner",
                parent_version_id=version.version_id,
                description="Replanned version after execution failure",
                context=replanning_context,
            )

            logger.info(
                f"Replanned workflow {workflow_id}: created version {new_version_id} "
                f"with {len(new_steps)} steps",
            )
            return new_version_id

        except Exception as e:
            logger.error(f"Error replanning workflow {workflow_id}: {str(e)}")
            return None

    def _create_replanning_context(
        self,
        steps: list[WorkflowStep],
        completed_steps: list[str],
        failed_steps: list[str],
        additional_context: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Create context information for replanning.

        Args:
            steps: List of all workflow steps
            completed_steps: List of completed step names
            failed_steps: List of failed step names
            additional_context: Optional additional context

        Returns:
            Dictionary containing replanning context
        """
        # Extract information about failed steps
        failed_step_info = []
        for step in steps:
            if step.task.name in failed_steps:
                failed_step_info.append({
                    "name": step.task.name,
                    "description": step.task.description,
                    "dependencies": step.dependencies,
                })

        # Create the context
        context = {
            "timestamp": datetime.now().isoformat(),
            "total_steps": len(steps),
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "completion_ratio": len(completed_steps) / max(1, len(steps)),
            "failed_step_details": failed_step_info,
        }

        # Add additional context if provided
        if additional_context:
            context.update(additional_context)

        return context

    async def optimize_workflow(
        self,
        workflow_id: str,
        version_id: str | None = None,
        optimization_strategy: str = "auto",
    ) -> str | None:
        """Optimize a workflow for better performance.

        Args:
            workflow_id: ID of the workflow to optimize
            version_id: Optional version ID (uses current version if not specified)
            optimization_strategy: Strategy to use for optimization

        Returns:
            ID of the optimized version, or None if optimization failed
        """
        if not self.workflow_optimizer:
            logger.warning("Cannot optimize workflow: no optimizer available")
            return None

        # Get the current version
        version = await self.workflow_history.get_version(workflow_id, version_id)
        if not version:
            logger.error(f"Cannot optimize: version not found for workflow {workflow_id}")
            return None

        try:
            # Optimize the workflow
            optimized_steps = await self.workflow_optimizer.optimize_workflow(
                version.steps, strategy=optimization_strategy,
            )

            # Create a new version with the optimized steps
            new_version_id = await self.workflow_history.create_version(
                workflow_id=workflow_id,
                steps=optimized_steps,
                created_by="workflow_optimizer",
                parent_version_id=version.version_id,
                description=f"Optimized version using {optimization_strategy} strategy",
            )

            logger.info(
                f"Optimized workflow {workflow_id}: created version {new_version_id} "
                f"with {len(optimized_steps)} steps",
            )
            return new_version_id

        except Exception as e:
            logger.error(f"Error optimizing workflow {workflow_id}: {str(e)}")
            return None