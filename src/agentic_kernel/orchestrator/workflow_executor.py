"""Workflow execution functionality for the orchestrator.

This module provides the WorkflowExecutor class, which is responsible for
executing workflows, managing step dependencies, and handling failures.
"""

import logging
from datetime import datetime
from typing import Any

from ..ledgers import ProgressLedger
from ..types import Task, WorkflowStep
from .agent_manager import AgentManager
from .condition_evaluator import ConditionalBranchManager
from .workflow_history import WorkflowHistory

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Executes workflows and manages their execution state.

    This class is responsible for:
    1. Executing workflow steps
    2. Managing step dependencies
    3. Handling step failures and retries
    4. Tracking workflow progress

    Attributes:
        agent_manager: Component for managing agents
        progress_ledger: Ledger for tracking workflow progress
        workflow_history: Component for tracking workflow versions and execution history
        branch_manager: Component for managing conditional branching in workflows
        max_inner_loop_iterations: Maximum number of iterations for the inner execution loop
        reflection_threshold: Progress threshold before reflection
    """

    def __init__(
        self,
        agent_manager: AgentManager,
        progress_ledger: ProgressLedger,
        workflow_history: WorkflowHistory,
    ):
        """Initialize the workflow executor.

        Args:
            agent_manager: Component for managing agents
            progress_ledger: Ledger for tracking workflow progress
            workflow_history: Component for tracking workflow versions and execution history
        """
        self.agent_manager = agent_manager
        self.progress_ledger = progress_ledger
        self.workflow_history = workflow_history
        self.branch_manager = ConditionalBranchManager()
        self.max_inner_loop_iterations = 10
        self.reflection_threshold = 0.7  # Progress threshold before reflection

    async def execute_workflow(
        self, workflow_id: str, version_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute a workflow.

        Args:
            workflow_id: ID of the workflow to execute
            version_id: Optional version ID (uses current version if not specified)

        Returns:
            Dictionary containing workflow execution results
        """
        # Get the workflow version to execute
        version = await self.workflow_history.get_version(workflow_id, version_id)
        if not version:
            error_msg = (
                f"Workflow version not found: {workflow_id}/{version_id or 'current'}"
            )
            logger.error(error_msg)
            return {"status": "failed", "error": error_msg}

        # Start execution record in history
        execution = await self.workflow_history.start_execution(
            workflow_id, version.version_id,
        )
        execution_id = execution.execution_id

        # Register workflow with progress ledger
        await self.progress_ledger.register_workflow(execution_id, version.steps)

        # Initialize workflow tracking variables
        completed_steps = []
        failed_steps = []
        retried_steps = []
        skipped_steps = []  # Track skipped steps due to conditions
        metrics = {
            "execution_time": 0.0,
            "resource_usage": {},
            "success_rate": 0.0,
            "replanning_count": 0,
        }

        # Initialize branch manager with workflow context
        self.branch_manager = ConditionalBranchManager(
            {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "version_id": version.version_id,
                "start_time": datetime.now().isoformat(),
            },
        )

        start_time = datetime.now()

        try:
            # INNER LOOP: Manages the progress ledger and step execution
            inner_loop_iterations = 0
            while inner_loop_iterations < self.max_inner_loop_iterations:
                inner_loop_iterations += 1

                # Check if workflow is complete by counting steps actually executed or skipped
                total_handled_steps = (
                    len(completed_steps) + len(failed_steps) + len(skipped_steps)
                )
                if total_handled_steps >= len(version.steps):
                    logger.info("Workflow execution completed")
                    break

                # Check for looping behavior
                if inner_loop_iterations > len(version.steps) * 2:
                    logger.warning("Possible loop detected in workflow execution")
                    break

                # Get executable steps (those whose dependencies are satisfied)
                executable_steps = self._get_executable_steps(
                    version.steps, completed_steps, failed_steps,
                )
                if not executable_steps:
                    logger.info("No more executable steps")
                    break

                # Execute each executable step
                for step in executable_steps:
                    # Check if step should be skipped based on condition
                    if step.condition and not self.branch_manager.evaluate_condition(
                        step.condition,
                    ):
                        logger.info(
                            f"Skipping step {step.task.name} due to condition: {step.condition}",
                        )
                        skipped_steps.append(step.task.name)
                        continue

                    # Execute the step
                    result = await self._execute_step(step.task)

                    # Record the result in workflow history
                    await self.workflow_history.record_step_result(
                        execution_id=execution_id,
                        step_name=step.task.name,
                        result=result,
                    )

                    # Record result in branch manager for conditional branching
                    self.branch_manager.record_step_result(step.task.name, result)

                    # Update tracking based on result
                    if result.get("status") == "success":
                        completed_steps.append(step.task.name)
                    else:
                        failed_steps.append(step.task.name)

                # Evaluate progress and potentially break for replanning
                progress_ratio = len(completed_steps) / len(version.steps)
                if (
                    failed_steps
                    and progress_ratio < self.reflection_threshold
                    and inner_loop_iterations > 1
                ):
                    logger.info(
                        f"Breaking inner loop for potential replanning. "
                        f"Progress: {progress_ratio:.2f}, Failed steps: {len(failed_steps)}",
                    )
                    break

            # Calculate final metrics
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            metrics["execution_time"] = execution_time

            # Calculate success rate
            total_steps = len(version.steps)
            if total_steps > 0:
                metrics["success_rate"] = len(completed_steps) / total_steps

            # Determine final status
            if failed_steps:
                status = "partial_success" if completed_steps else "failed"
            else:
                status = "success"

            # Complete execution record in history
            await self.workflow_history.complete_execution(execution_id, status)

            return {
                "status": status,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "skipped_steps": skipped_steps,
                "retried_steps": retried_steps,
                "metrics": metrics,
                "execution_id": execution_id,
            }

        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            
            # Complete execution record in history with failed status
            await self.workflow_history.complete_execution(execution_id, "failed")
            
            return {
                "status": "failed",
                "error": str(e),
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "execution_id": execution_id,
            }

    async def _execute_step(self, task: Task) -> dict[str, Any]:
        """Execute a single step in the workflow.

        Args:
            task: The task to execute

        Returns:
            Dictionary containing step execution results
        """
        try:
            # Select an agent for the task
            agent = await self.agent_manager.select_agent_for_task(task)
            if not agent:
                return {
                    "status": "error",
                    "error": f"No suitable agent found for task: {task.name}",
                }

            # Execute the task
            start_time = datetime.now()
            result = await agent.execute(task)
            execution_time = (datetime.now() - start_time).total_seconds()

            # Ensure result is a dictionary
            if not isinstance(result, dict):
                result = {"output": result}

            # Add execution metrics
            metrics = result.get("metrics", {})
            metrics["execution_time"] = execution_time
            result["metrics"] = metrics

            # Ensure status is set
            if "status" not in result:
                result["status"] = "success"

            return result

        except Exception as e:
            logger.error(f"Error executing step {task.name}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "task_name": task.name,
            }

    def _get_executable_steps(
        self, steps: list[WorkflowStep], completed_steps: list[str], failed_steps: list[str],
    ) -> list[WorkflowStep]:
        """Get steps that can be executed based on their dependencies.

        Args:
            steps: List of all workflow steps
            completed_steps: List of completed step names
            failed_steps: List of failed step names

        Returns:
            List of executable workflow steps
        """
        executable = []
        handled_steps = completed_steps + failed_steps
        
        for step in steps:
            # Skip steps that have already been handled
            if step.task.name in handled_steps:
                continue
                
            # Check if all dependencies are satisfied
            dependencies_satisfied = all(
                dep in completed_steps for dep in step.dependencies
            )
            
            # Check if any dependencies have failed (if so, this step can't be executed)
            dependencies_failed = any(
                dep in failed_steps for dep in step.dependencies
            )
            
            if dependencies_satisfied and not dependencies_failed:
                executable.append(step)
                
        return executable