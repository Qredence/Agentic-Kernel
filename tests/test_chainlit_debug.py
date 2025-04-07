"""Test file for debugging Chainlit integration features.

This file provides a way to test the Chainlit integration with the
TaskManager and TaskList without requiring a full Chainlit server.
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Chainlit
mock_cl = MagicMock()
mock_cl.user_session = {}
mock_cl.Message = AsyncMock()
mock_cl.Step = AsyncMock()
mock_cl.__enter__ = AsyncMock()
mock_cl.__exit__ = AsyncMock()

# Create mock TaskList
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
        print(f"TaskList updated: {self.status} with {len(self.tasks)} tasks")
        for task in self.tasks:
            print(f"  - {task.title}: {task.status}")

# Add TaskStatus enum
class MockTaskStatus:
    READY = "ready"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

# Configure the mock
mock_cl.TaskList = MockTaskList
mock_cl.Task = MockTask
mock_cl.TaskStatus = MockTaskStatus

# Mock the chainlit module
sys.modules['chainlit'] = mock_cl

# Now import our app modules
from src.agentic_kernel.app import TaskManager
from src.agentic_kernel.types import Task
from src.agentic_kernel.ledgers.task_ledger import TaskLedger
from src.agentic_kernel.ledgers.progress_ledger import ProgressLedger

# Mock message object
class MockMessage:
    def __init__(self, content, author=None):
        self.content = content
        self.author = author
        self.id = f"msg_{datetime.now().timestamp()}"

    async def send(self):
        print(f"Message sent: {self.content[:30]}...")
        return self

    async def stream_token(self, content):
        print(f"Token streamed: {content[:30]}...")
        
    async def update(self):
        print("Message updated")

# Tests for TaskList integration
@pytest.mark.asyncio
async def test_task_manager_with_tasklist():
    """Test the TaskManager with a TaskList in a simulated Chainlit environment."""
    # Create TaskManager with ledgers
    task_ledger = TaskLedger()
    progress_ledger = ProgressLedger()
    task_manager = TaskManager(task_ledger, progress_ledger)
    
    # Create TaskList
    task_list = MockTaskList()
    
    print("\n=== Creating tasks with different statuses ===")
    
    # Create tasks with different statuses
    task1 = await task_manager.create_task(
        name="Initial task",
        agent_type="test",
        description="A task that starts in pending status",
        parameters={"param1": "value1"}
    )
    
    task2 = await task_manager.create_task(
        name="System task",
        agent_type="system",
        description="A system operation task",
        parameters={"system": True}
    )
    
    # Mark one task as completed
    await task_manager.complete_task(task2.id, {"result": "success"})
    
    print("\n=== Creating a message and linking to a task ===")
    # Create a message and link it
    message = MockMessage("Test message content")
    await message.send()
    
    await task_manager.link_message_to_task(message.id, task1.id)
    
    print("\n=== Syncing TaskManager with TaskList ===")
    # Sync with TaskList
    await task_manager.sync_with_chainlit_tasklist(task_list)
    
    print("\n=== Updating task status and syncing again ===")
    # Update task status and sync again
    await task_manager.complete_task(
        task1.id, 
        {"result": "completed successfully"}
    )
    
    await task_manager.sync_with_chainlit_tasklist(task_list)
    
    print("\n=== Creating a failed task and syncing ===")
    # Create a failed task
    task3 = await task_manager.create_task(
        name="Failing task",
        agent_type="test",
        description="A task that will fail"
    )
    
    await task_manager.fail_task(task3.id, "Something went wrong")
    
    await task_manager.sync_with_chainlit_tasklist(task_list)
    
    # Assertions to verify the test is working correctly
    assert len(task_list.tasks) == 3, f"Expected 3 tasks, got {len(task_list.tasks)}"
    assert task_list.status == "Ready", f"Expected status 'Ready', got '{task_list.status}'"
    
    print("\n=== Test completed successfully ===")

if __name__ == "__main__":
    # We can run this directly for debugging
    asyncio.run(test_task_manager_with_tasklist()) 