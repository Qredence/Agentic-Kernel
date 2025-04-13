"""Test file for debugging Chainlit integration features.

This file provides a way to test the Chainlit integration with the
TaskManager and TaskList without requiring a full Chainlit server.
"""

import asyncio
from datetime import datetime, timezone
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock Chainlit needs to be defined before importing app modules
mock_cl = MagicMock()
mock_cl.user_session = {}
mock_cl.Message = AsyncMock()
mock_cl.Step = AsyncMock()
mock_cl.__enter__ = AsyncMock()
mock_cl.__exit__ = AsyncMock()
mock_cl.set_chat_profiles = MagicMock()  # Add mock for set_chat_profiles

# Mock the chainlit module - MUST happen before importing app modules
sys.modules["chainlit"] = mock_cl

# Now import our app modules that depend on the mocked chainlit
from src.agentic_kernel.app import TaskManager  # noqa: E402
from src.agentic_kernel.ledgers.progress_ledger import ProgressLedger  # noqa: E402
from src.agentic_kernel.ledgers.task_ledger import TaskLedger  # noqa: E402

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
        pass

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

# Mock message object
class MockMessage:
    def __init__(self, content, author=None):
        self.content = content
        self.author = author
        self.id = f"msg_{datetime.now(timezone.utc).timestamp()}"

    async def send(self):
        return self

    async def stream_token(self, content):
        pass

    async def update(self):
        pass


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

    # Create tasks with different statuses
    task1 = await task_manager.create_task(
        name="Initial task",
        agent_type="test",
        description="A task that starts in pending status",
        parameters={"param1": "value1"},
    )

    task2 = await task_manager.create_task(
        name="System task",
        agent_type="system",
        description="A system operation task",
        parameters={"system": True},
    )

    # Mark one task as completed
    await task_manager.complete_task(task2.id, {"result": "success"})

    # Create a message and link it
    message = MockMessage("Test message content")
    await message.send()

    await task_manager.link_message_to_task(message.id, task1.id)

    # Sync with TaskList
    await task_manager.sync_with_chainlit_tasklist(task_list)

    # Update task status and sync again
    await task_manager.complete_task(task1.id, {"result": "completed successfully"})

    await task_manager.sync_with_chainlit_tasklist(task_list)

    # Create a failed task
    task3 = await task_manager.create_task(
        name="Failing task", agent_type="test", description="A task that will fail",
    )

    await task_manager.fail_task(task3.id, "Simulated failure")

    await task_manager.sync_with_chainlit_tasklist(task_list)

    # Assertions to verify the test is working correctly
    assert len(task_list.tasks) == 3, f"Expected 3 tasks, got {len(task_list.tasks)}"  # noqa: S101
    assert task_list.status == "Ready", (f"Expected status 'Ready', got '{task_list.status}'")  # noqa: S101


if __name__ == "__main__":
    # We can run this directly for debugging
    asyncio.run(test_task_manager_with_tasklist())
