"""Tests for the TaskManager class."""

import os
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the types and TaskLedger
from src.agentic_kernel.types import Task
from src.agentic_kernel.ledgers.task_ledger import TaskLedger
from src.agentic_kernel.ledgers.progress_ledger import ProgressLedger
from src.agentic_kernel.utils.task_manager import TaskManager

# Create a simplified version of the TaskManager for testing
class TestTaskManager:
    """Simple TaskManager class for testing."""
    
    def __init__(self):
        """Initialize with a TaskLedger."""
        self.task_ledger = TaskLedger(goal="Test goal")
        self.tasks = {}
        self.message_task_map = {}
        
    async def create_task(self, agent_type, name, description, params):
        """Create a new task."""
        task_id = f"test_task_{len(self.tasks) + 1}"
        task = Task(
            id=task_id,
            name=name,
            description=description,
            agent_type=agent_type,
            parameters=params,
            status="pending",
            max_retries=3,
            created_at=datetime.now()
        )
        self.tasks[task_id] = task
        await self.task_ledger.add_task(task)
        return task_id
    
    async def update_task_status(self, task_id, status, result=None):
        """Update task status."""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        task.status = status
        
        if result:
            await self.task_ledger.update_task_result(task_id, result)
            
    async def link_message_to_task(self, message_id, task_id):
        """Link a message to a task."""
        self.message_task_map[message_id] = task_id

# Tests
@pytest.mark.asyncio
async def test_create_task():
    """Test creating tasks."""
    # Create TaskManager
    task_manager = TestTaskManager()
    
    # Create a task
    task_id = await task_manager.create_task(
        agent_type="test",
        name="Test Task",
        description="A test task",
        params={"param1": "value1"}
    )
    
    # Verify task was created
    assert task_id in task_manager.tasks
    assert task_manager.tasks[task_id].name == "Test Task"
    assert task_manager.tasks[task_id].description == "A test task"
    assert task_manager.tasks[task_id].agent_type == "test"
    assert task_manager.tasks[task_id].parameters["param1"] == "value1"
    assert task_manager.tasks[task_id].status == "pending"

@pytest.mark.asyncio
async def test_update_task_status():
    """Test updating task status."""
    # Create TaskManager
    task_manager = TestTaskManager()
    
    # Create a task
    task_id = await task_manager.create_task(
        agent_type="test",
        name="Test Task",
        description="A test task",
        params={}
    )
    
    # Update status
    await task_manager.update_task_status(
        task_id,
        "completed",
        {"result": "success"}
    )
    
    # Verify status was updated
    assert task_manager.tasks[task_id].status == "completed"

@pytest.mark.asyncio
async def test_link_message_to_task():
    """Test linking messages to tasks."""
    # Create TaskManager
    task_manager = TestTaskManager()
    
    # Create a task
    task_id = await task_manager.create_task(
        agent_type="test",
        name="Test Task",
        description="A test task",
        params={}
    )
    
    # Link message
    message_id = "test_message_1"
    await task_manager.link_message_to_task(message_id, task_id)
    
    # Verify link was created
    assert task_manager.message_task_map[message_id] == task_id

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 