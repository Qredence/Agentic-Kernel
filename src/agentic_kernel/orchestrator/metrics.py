"""Metrics and progress calculation for workflow execution."""

import logging
from typing import List, Dict, Any
from ..types import WorkflowStep

logger = logging.getLogger(__name__)


def calculate_progress(
    workflow: List[WorkflowStep], completed_steps: List[str], failed_steps: List[str]
) -> float:
    """Calculate the current progress of a workflow.

    Args:
        workflow: List of workflow steps
        completed_steps: List of completed step names
        failed_steps: List of failed step names

    Returns:
        Progress as a float between 0 and 1
    """
    if not workflow:
        return 1.0

    total_steps = len(workflow)
    completed_count = len(completed_steps)
    failed_count = len(failed_steps)

    # Weight completed steps more heavily than failed ones
    progress = (completed_count + (failed_count * 0.5)) / total_steps
    return min(max(progress, 0.0), 1.0)


async def should_replan(
    workflow: List[WorkflowStep], completed_steps: List[str], failed_steps: List[str]
) -> bool:
    """Determine if workflow replanning is needed.

    Args:
        workflow: List of workflow steps
        completed_steps: List of completed step names
        failed_steps: List of failed step names

    Returns:
        True if replanning is needed, False otherwise
    """
    # If no failures, no need to replan
    if not failed_steps:
        return False

    # If all steps are either completed or failed, no point in replanning
    if len(completed_steps) + len(failed_steps) >= len(workflow):
        return False

    # If critical steps have failed, we should replan
    critical_failures = any(
        step.task.critical for step in workflow if step.task.name in failed_steps
    )
    if critical_failures:
        logger.info("Critical step failures detected, replanning needed")
        return True

    # If too many failures relative to progress, we should replan
    failure_ratio = len(failed_steps) / len(workflow)
    if failure_ratio > 0.3:  # More than 30% failures
        logger.info(f"High failure ratio ({failure_ratio:.2f}), replanning needed")
        return True

    return False


def collect_step_metrics(step_result: Dict[str, Any]) -> Dict[str, Any]:
    """Collect metrics from a step execution result.

    Args:
        step_result: Result dictionary from step execution

    Returns:
        Dictionary of metrics
    """
    metrics = {
        "execution_time": step_result.get("execution_time", 0.0),
        "memory_usage": step_result.get("memory_usage", 0.0),
        "api_calls": step_result.get("api_calls", 0),
        "retries": step_result.get("retries", 0),
    }

    # Add any custom metrics from the step
    custom_metrics = step_result.get("custom_metrics", {})
    metrics.update(custom_metrics)

    return metrics
