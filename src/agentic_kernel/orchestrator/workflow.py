"""Workflow execution and planning logic for the orchestrator."""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ..types import Task, WorkflowStep

logger = logging.getLogger(__name__)


async def execute_workflow(self, workflow: List[WorkflowStep]) -> Dict[str, Any]:
    """Execute a workflow.

    Args:
        workflow: List of workflow steps to execute

    Returns:
        Dictionary containing workflow execution results
    """
    workflow_id = f"workflow_{datetime.now().timestamp()}"
    await self.progress_ledger.register_workflow(workflow_id, workflow)

    # Initialize workflow tracking variables
    completed_steps = []
    failed_steps = []
    retried_steps = []
    replanned = False
    planning_attempts = 0
    metrics = {
        "execution_time": 0.0,
        "resource_usage": {},
        "success_rate": 0.0,
        "replanning_count": 0,
    }

    start_time = datetime.now()

    try:
        # OUTER LOOP: Manages the task ledger and planning
        while planning_attempts < self.max_planning_attempts:
            planning_attempts += 1

            if planning_attempts > 1:
                # Re-plan the workflow
                logger.info(f"Re-planning workflow (attempt {planning_attempts})")
                metrics["replanning_count"] += 1
                try:
                    workflow = await self._replan_workflow(
                        workflow_id, workflow, completed_steps, failed_steps
                    )
                    replanned = True
                    # Reset states for all agents
                    for agent in self.agents.values():
                        await self._reset_agent_state(agent)
                except Exception as e:
                    logger.error(f"Failed to replan workflow: {str(e)}")
                    break

            inner_loop_iterations = 0

            # INNER LOOP: Manages the progress ledger and step execution
            while inner_loop_iterations < self.max_inner_loop_iterations:
                inner_loop_iterations += 1

                # Check if workflow is complete
                if len(completed_steps) + len(failed_steps) >= len(workflow):
                    logger.info("Workflow execution completed")
                    break

                # Check for looping behavior
                if inner_loop_iterations > len(workflow) * 2:
                    logger.warning("Possible loop detected in workflow execution")
                    break

                # Get steps ready for execution
                ready_steps = self.progress_ledger.get_ready_steps(workflow_id)

                if not ready_steps:
                    # Check for deadlock
                    remaining = (
                        set(step.task.name for step in workflow)
                        - set(completed_steps)
                        - set(failed_steps)
                    )
                    if remaining and not ready_steps:
                        logger.warning(
                            f"Potential deadlock detected. Remaining steps: {remaining}"
                        )
                        break
                    await asyncio.sleep(0.1)
                    continue

                # Execute ready steps in sequence (for deterministic execution)
                for step_name in ready_steps:
                    step = next(s for s in workflow if s.task.name == step_name)
                    result = await self._execute_step(workflow_id, step)

                    # Process result
                    if isinstance(result, Exception) or (
                        isinstance(result, dict) and result.get("status") != "success"
                    ):
                        error_msg = (
                            str(result)
                            if isinstance(result, Exception)
                            else result.get("error", "Unknown error")
                        )
                        logger.error(f"Step {step_name} failed: {error_msg}")
                        failed_steps.append(step_name)
                        await self.progress_ledger.update_step_status(
                            workflow_id, step_name, "failed"
                        )

                        # Assess if we need to break the inner loop and replan
                        if await self._should_replan(
                            workflow, completed_steps, failed_steps
                        ):
                            break
                    else:
                        if result.get("retried", False):
                            retried_steps.append(step_name)
                        completed_steps.append(step_name)
                        await self.progress_ledger.update_step_status(
                            workflow_id, step_name, "completed"
                        )

                        # Update metrics
                        step_metrics = result.get("metrics", {})
                        for key, value in step_metrics.items():
                            if key not in metrics["resource_usage"]:
                                metrics["resource_usage"][key] = 0
                            metrics["resource_usage"][key] += value

                # Check for progress
                progress = self._calculate_progress(
                    workflow, completed_steps, failed_steps
                )
                if progress < self.reflection_threshold and inner_loop_iterations > 3:
                    logger.info(
                        f"Insufficient progress ({progress:.2f}). Breaking inner loop to reflect and replan."
                    )
                    break

            # Check if workflow is complete after inner loop
            if (
                len(completed_steps) + len(failed_steps) >= len(workflow)
                and len(failed_steps) == 0
            ):
                logger.info("Workflow execution completed successfully")
                break

            # Check if no more replanning is needed
            if not await self._should_replan(workflow, completed_steps, failed_steps):
                break

    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "replanned": replanned,
            "metrics": metrics,
        }

    # Calculate final metrics
    end_time = datetime.now()
    metrics["execution_time"] = (end_time - start_time).total_seconds()
    metrics["success_rate"] = len(completed_steps) / len(workflow) if workflow else 1.0

    return {
        "status": "success" if not failed_steps else "partial_success",
        "completed_steps": completed_steps,
        "failed_steps": failed_steps,
        "retried_steps": retried_steps,
        "replanned": replanned,
        "metrics": metrics,
    }


async def create_dynamic_workflow(
    self, goal: str, context: Optional[Dict[str, Any]] = None
) -> List[WorkflowStep]:
    """Create a dynamic workflow based on a goal.

    Args:
        goal: The goal to achieve
        context: Optional context information

    Returns:
        List of workflow steps
    """
    try:
        # Get the planning agent
        planner = self.agents.get("planner")
        if not planner:
            raise ValueError("No planning agent registered")

        # Create initial plan
        plan_result = await planner.execute(
            {
                "goal": goal,
                "context": context or {},
                "available_agents": list(self.agents.keys()),
            }
        )

        if not plan_result or not isinstance(plan_result, dict):
            raise ValueError("Invalid plan result from planner")

        workflow = plan_result.get("workflow", [])
        if not workflow:
            raise ValueError("Empty workflow returned from planner")

        # Validate workflow steps
        for step in workflow:
            if not isinstance(step, WorkflowStep):
                raise ValueError(f"Invalid workflow step: {step}")

        return workflow

    except Exception as e:
        logger.error(f"Failed to create dynamic workflow: {str(e)}")
        raise
