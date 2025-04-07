"""Tests for TaskList integration with TaskManager in Chainlit.

These tests verify that the TaskManager properly interacts with the Chainlit TaskList element,
ensuring task status is correctly synchronized between the internal ledger and the UI.
"""

import os
import sys
import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agentic_kernel.types import Task
from src.agentic_kernel.ledgers.task_ledger import TaskLedger
from src.agentic_kernel.ledgers.progress_ledger import ProgressLedger
from src.agentic_kernel.utils.task_manager import TaskManager

# Mock Chainlit dependencies
class MockTask:
    def __init__(self, title, status=None):
        self.title = title
        self.status = status
        self.forId = None

class MockTaskList:
    def __init__(self):
        self.tasks = []
        self.status = "Ready"
    
    async def add_task(self, task):
        self.tasks.append(task)
    
    async def send(self):
        # This would update the UI in a real Chainlit app
        pass

# Patch chainlit module
sys.modules['chainlit'] = MagicMock()
cl = sys.modules['chainlit']
cl.Task = MockTask
cl.TaskList = MockTaskList
cl.TaskStatus = MagicMock()
cl.TaskStatus.READY = "ready"
cl.TaskStatus.RUNNING = "running"
cl.TaskStatus.DONE = "done"
cl.TaskStatus.FAILED = "failed"

@pytest.fixture
def task_manager():
    """Create a TaskManager instance for testing."""
    task_ledger = TaskLedger()
    progress_ledger = ProgressLedger()
    return TaskManager(task_ledger, progress_ledger)

@pytest.fixture
def mock_tasklist():
    """Create a mock TaskList for testing."""
    return MockTaskList()

@pytest.mark.asyncio
async def test_create_task(task_manager):
    """Test task creation in TaskManager."""
    task = await task_manager.create_task(
        name="test_task",
        agent_type="test",
        description="Test task description",
        parameters={"test_param": "test_value"}
    )
    
    # Verify task was created correctly
    assert task.name == "test_task"
    assert task.description == "Test task description"
    assert task.agent_type == "test"
    assert task.parameters["test_param"] == "test_value"
    assert task.status == "pending"
    
    # Verify task is in ledger
    stored_task = await task_manager.get_task(task.id)
    assert stored_task is not None
    assert stored_task.name == task.name

@pytest.mark.asyncio
async def test_update_task_status(task_manager):
    """Test updating task status."""
    task = await task_manager.create_task(
        name="test_task",
        agent_type="test",
        description="Test task description"
    )
    
    await task_manager.update_task_status(
        task.id, 
        "completed", 
        {"result": "success"}
    )
    
    updated_task = await task_manager.get_task(task.id)
    assert updated_task.status == "completed"

@pytest.mark.asyncio
async def test_link_message_to_task(task_manager):
    """Test linking a message to a task."""
    task = await task_manager.create_task(
        name="test_task",
        agent_type="test",
        description="Test task description"
    )
    
    message_id = "test_message_id"
    await task_manager.link_message_to_task(message_id, task.id)
    
    assert task_manager.message_task_map[message_id] == task.id

@pytest.mark.asyncio
async def test_sync_with_chainlit_tasklist(task_manager, mock_tasklist):
    """Test synchronizing TaskManager with Chainlit TaskList."""
    # Create multiple tasks with different statuses
    task1 = await task_manager.create_task(
        name="pending_task",
        agent_type="test",
        description="A pending task"
    )
    
    task2 = await task_manager.create_task(
        name="completed_task",
        agent_type="test",
        description="A completed task"
    )
    await task_manager.complete_task(task2.id, {"result": "success"})
    
    task3 = await task_manager.create_task(
        name="failed_task",
        agent_type="test",
        description="A failed task"
    )
    await task_manager.fail_task(task3.id, "Test failure")
    
    # Link message to one task
    message_id = "test_message_id"
    await task_manager.link_message_to_task(message_id, task1.id)
    
    # Sync with TaskList
    await task_manager.sync_with_chainlit_tasklist(mock_tasklist)
    
    # Verify TaskList state
    assert len(mock_tasklist.tasks) == 3
    
    # Check status mapping
    status_mapping = {
        task.title: task.status for task in mock_tasklist.tasks
    }
    assert any("pending_task" in title and status == "running" 
               for title, status in status_mapping.items())
    assert any("completed_task" in title and status == "done" 
               for title, status in status_mapping.items())
    assert any("failed_task" in title and status == "failed" 
               for title, status in status_mapping.items())
    
    # Check message linking
    for task in mock_tasklist.tasks:
        if "pending_task" in task.title:
            assert task.forId == message_id
        else:
            assert task.forId is None or task.forId != message_id
    
    # Task list status should reflect overall status
    assert mock_tasklist.status == "Processing"

@pytest.mark.asyncio
async def test_tasklist_all_completed(task_manager, mock_tasklist):
    """Test TaskList status when all tasks are completed."""
    task = await task_manager.create_task(
        name="completed_task",
        agent_type="test",
        description="A completed task"
    )
    await task_manager.complete_task(task.id, {"result": "success"})
    
    await task_manager.sync_with_chainlit_tasklist(mock_tasklist)
    
    assert mock_tasklist.status == "Ready"
    assert len(mock_tasklist.tasks) == 1
    assert mock_tasklist.tasks[0].status == "done"

@pytest.mark.asyncio
async def test_tasklist_all_failed(task_manager, mock_tasklist):
    """Test TaskList status when all tasks failed."""
    task = await task_manager.create_task(
        name="failed_task",
        agent_type="test",
        description="A failed task"
    )
    await task_manager.fail_task(task.id, "Test failure")
    
    await task_manager.sync_with_chainlit_tasklist(mock_tasklist)
    
    assert mock_tasklist.status == "Ready"
    assert len(mock_tasklist.tasks) == 1
    assert mock_tasklist.tasks[0].status == "failed"

if __name__ == "__main__":
    # For direct execution during development
    pytest.main(["-xvs", __file__]) 