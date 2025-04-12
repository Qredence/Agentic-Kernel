"""Tests for ValidatorAgent."""

import pytest
import asyncio
from ..agents.validator import ValidatorAgent
from examples.adk_multi_agent.agents.task_manager import TaskManagerAgent
from examples.adk_multi_agent.agents.worker import WorkerAgent

@pytest.mark.asyncio
async def test_validate_task(validator, task_manager, worker):
    """Test task validation."""
    # Create and execute a task
    task_result = await task_manager.create_task(
        task_description="Test task",
        priority="high"
    )
    await worker.execute_task(task_result["activity_id"])
    
    # Add a small delay to allow state propagation
    await asyncio.sleep(0.1)
    
    # Validate the task
    result = await validator.validate_task(task_result["activity_id"])
    
    assert "activity_id" in result
    assert result["status"] == "valid"
    assert "feedback" in result

@pytest.mark.asyncio
async def test_validate_invalid_task(validator):
    """Test validation of invalid task."""
    # Try to validate a non-existent task
    result = await validator.validate_task("invalid_id")
    
    assert "activity_id" in result
    assert result["status"] == "invalid"
    assert "reason" in result

@pytest.mark.asyncio
async def test_update_trust(validator):
    """Test trust update."""
    result = await validator.update_trust(
        agent_id="worker_agent",
        success=True
    )
    
    assert "agent_id" in result
    assert "trust_score" in result
    assert result["status"] == "updated" 