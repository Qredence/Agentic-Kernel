"""Tests for TaskList synchronization.

Tests the ability to synchronize tasks from the TaskManager to a Chainlit TaskList
using the mock Chainlit components.
"""

import os
import sys
import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the mocks
from tests.mocks.chainlit import Task as MockTask
from tests.mocks.chainlit import TaskList as MockTaskList
from tests.mocks.chainlit import TaskStatus as MockTaskStatus

# Import the real types
from src.agentic_kernel.types import Task
from src.agentic_kernel.ledgers.task_ledger import TaskLedger

# Define a TaskManager with TaskList synchronization for testing
class SyncTestTaskManager:
    """Task manager with TaskList synchronization for testing."""
    
    def __init__(self):
        """Initialize with a TaskLedger."""
        self.task_ledger = TaskLedger(goal="Test synchronization goal")
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
        
    async def sync_with_chainlit_tasklist(self, task_list):
        """Sync the current tasks with a Chainlit TaskList."""
        if not task_list:
            return
            
        # Clear existing tasks if any
        task_list.tasks.clear()
            
        # Add tasks from the task dictionary
        for task_id, task in self.tasks.items():
            # Map status to MockTaskStatus
            if task.status == "pending":
                cl_status = MockTaskStatus.RUNNING
            elif task.status == "completed":
                cl_status = MockTaskStatus.DONE
            elif task.status == "failed":
                cl_status = MockTaskStatus.FAILED
            else:
                cl_status = MockTaskStatus.READY
                
            # Create the MockTask
            cl_task = MockTask(
                title=f"{task.name}: {task.description[:50]}...",
                status=cl_status
            )
            
            # Link to message if available
            for msg_id, linked_task_id in self.message_task_map.items():
                if linked_task_id == task_id:
                    cl_task.forId = msg_id
                    break
                    
            # Add task to the TaskList
            await task_list.add_task(cl_task)
            
        # Update TaskList status based on task statuses
        pending_tasks = any(task.status == "pending" for task in self.tasks.values())
        failed_tasks = any(task.status == "failed" for task in self.tasks.values())
        
        if pending_tasks:
            task_list.status = "Processing"
        elif failed_tasks:
            task_list.status = "Failed"
        else:
            task_list.status = "Ready"
            
        # Send to UI (mocked)
        await task_list.send()

# Tests
@pytest.mark.asyncio
async def test_task_list_sync_empty():
    """Test synchronizing an empty task list."""
    task_manager = SyncTestTaskManager()
    task_list = MockTaskList()
    
    # Sync with empty tasks
    await task_manager.sync_with_chainlit_tasklist(task_list)
    
    # Verify
    assert len(task_list.tasks) == 0
    assert task_list.status == "Ready"

@pytest.mark.asyncio
async def test_task_list_sync_with_tasks():
    """Test synchronizing a task list with multiple tasks."""
    task_manager = SyncTestTaskManager()
    task_list = MockTaskList()
    
    # Create tasks with different statuses
    task_id1 = await task_manager.create_task(
        agent_type="web",
        name="Search Web",
        description="Search for information on the web",
        params={"query": "test query"}
    )
    
    task_id2 = await task_manager.create_task(
        agent_type="file",
        name="Read File",
        description="Read content from a file",
        params={"path": "test/file.txt"}
    )
    
    # Update task statuses
    await task_manager.update_task_status(task_id1, "completed", {"result": "success"})
    
    # Sync with TaskList
    await task_manager.sync_with_chainlit_tasklist(task_list)
    
    # Verify
    assert len(task_list.tasks) == 2
    
    # Check status mapping
    task_statuses = {task.title.split(':')[0].strip(): task.status for task in task_list.tasks}
    assert any("Search Web" in title and status == MockTaskStatus.DONE 
               for title, status in task_statuses.items())
    assert any("Read File" in title and status == MockTaskStatus.RUNNING 
               for title, status in task_statuses.items())
    
    # TaskList status should show "Processing" since one task is still pending
    assert task_list.status == "Processing"

@pytest.mark.asyncio
async def test_task_list_sync_with_message_linking():
    """Test synchronizing a task list with message linking."""
    task_manager = SyncTestTaskManager()
    task_list = MockTaskList()
    
    # Create a task
    task_id = await task_manager.create_task(
        agent_type="test",
        name="Test Task",
        description="A test task with message linking",
        params={}
    )
    
    # Link a message
    message_id = "message_123"
    await task_manager.link_message_to_task(message_id, task_id)
    
    # Sync with TaskList
    await task_manager.sync_with_chainlit_tasklist(task_list)
    
    # Verify
    assert len(task_list.tasks) == 1
    assert task_list.tasks[0].forId == message_id
    
@pytest.mark.asyncio
async def test_task_list_sync_with_failed_task():
    """Test synchronizing a task list with a failed task."""
    task_manager = SyncTestTaskManager()
    task_list = MockTaskList()
    
    # Create a task
    task_id = await task_manager.create_task(
        agent_type="test",
        name="Failing Task",
        description="A task that will fail",
        params={}
    )
    
    # Mark as failed
    await task_manager.update_task_status(task_id, "failed", {"error": "Test error"})
    
    # Sync with TaskList
    await task_manager.sync_with_chainlit_tasklist(task_list)
    
    # Verify
    assert len(task_list.tasks) == 1
    assert task_list.tasks[0].status == MockTaskStatus.FAILED
    assert task_list.status == "Failed"

if __name__ == "__main__":
    # Run this directly for debugging
    pytest.main(["-xvs", __file__]) 