"""Tests for WorkerAgent."""

import pytest
import asyncio
from ..agents.worker import WorkerAgent
from examples.adk_multi_agent.agents.task_manager import TaskManagerAgent

@pytest.mark.asyncio
async def test_execute_task(worker, task_manager):
    """Test task execution."""
    # Create a task first
    task_result = await task_manager.create_task(
        task_description="Test task",
        priority="high"
    )
    
    # Execute the task
    result = await worker.execute_task(task_result["activity_id"])
    
    assert "activity_id" in result
    assert result["status"] == "completed"
    assert "result" in result

@pytest.mark.asyncio
async def test_report_progress(worker, task_manager):
    """Test progress reporting."""
    # Create a task first
    task_result = await task_manager.create_task(
        task_description="Test task",
        priority="high"
    )
    
    # Report progress
    result = await worker.report_progress(task_result["activity_id"])
    
    assert "activity_id" in result
    assert "status" in result
    assert "progress" in result 