"""Tests for TaskManagerAgent."""

import pytest
from datetime import datetime, timedelta
from ..agents.task_manager import TaskManagerAgent

@pytest.mark.asyncio
async def test_create_task(task_manager):
    """Test task creation."""
    task_description = "Test task"
    priority = "high"
    deadline = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    
    result = await task_manager.create_task(
        task_description=task_description,
        priority=priority,
        deadline=deadline
    )
    
    assert "activity_id" in result
    assert result["status"] == "created"
    assert result["assigned_to"] == "worker_agent"

@pytest.mark.asyncio
async def test_create_task_no_deadline(task_manager):
    """Test task creation without deadline."""
    task_description = "Test task"
    priority = "high"
    
    result = await task_manager.create_task(
        task_description=task_description,
        priority=priority
    )
    
    assert "activity_id" in result
    assert result["status"] == "created"
    assert result["assigned_to"] == "worker_agent"

@pytest.mark.asyncio
async def test_monitor_tasks(task_manager):
    """Test task monitoring."""
    # Create a task first
    await task_manager.create_task(
        task_description="Test task",
        priority="high"
    )
    
    # Monitor tasks
    timeline = await task_manager.monitor_tasks()
    
    assert isinstance(timeline, list)
    assert len(timeline) > 0 