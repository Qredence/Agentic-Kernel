"""Tests for the TaskLedger and ProgressLedger classes."""

import pytest
from datetime import datetime
from agentic_kernel.ledgers.task_ledger import TaskLedger
from agentic_kernel.ledgers.progress_ledger import ProgressLedger
from agentic_kernel.types import Task, WorkflowStep

# --- TaskLedger Tests ---

@pytest.fixture
def task_ledger():
    """Create a TaskLedger instance."""
    return TaskLedger()

@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        name="test_task",
        agent_type="test_agent",
        max_retries=1,
        description="Test task",
        metadata={"priority": "high"}
    )

@pytest.mark.asyncio
async def test_task_ledger_add_task(task_ledger, sample_task):
    """Test adding a task to the ledger."""
    task_id = await task_ledger.add_task(sample_task)
    
    assert task_id is not None
    assert task_id in task_ledger.tasks
    assert task_ledger.tasks[task_id]["task"] == sample_task
    assert task_ledger.tasks[task_id]["status"] == "pending"
    assert isinstance(task_ledger.tasks[task_id]["created_at"], datetime)

@pytest.mark.asyncio
async def test_task_ledger_update_task_result(task_ledger, sample_task):
    """Test updating a task result."""
    task_id = await task_ledger.add_task(sample_task)
    result = {"status": "success", "output": "test output"}
    
    await task_ledger.update_task_result(task_id, result)
    
    assert task_ledger.tasks[task_id]["result"] == result
    assert task_ledger.tasks[task_id]["status"] == "completed"
    assert isinstance(task_ledger.tasks[task_id]["completed_at"], datetime)

@pytest.mark.asyncio
async def test_task_ledger_get_task_status(task_ledger, sample_task):
    """Test getting task status."""
    task_id = await task_ledger.add_task(sample_task)
    status = await task_ledger.get_task_status(task_id)
    
    assert status == "pending"
    
    # Update task and check new status
    await task_ledger.update_task_result(task_id, {"status": "success"})
    status = await task_ledger.get_task_status(task_id)
    
    assert status == "completed"

@pytest.mark.asyncio
async def test_task_ledger_invalid_task_id(task_ledger):
    """Test handling of invalid task IDs."""
    with pytest.raises(KeyError):
        await task_ledger.get_task_status("nonexistent")
    
    with pytest.raises(KeyError):
        await task_ledger.update_task_result("nonexistent", {})

# --- ProgressLedger Tests ---

@pytest.fixture
def progress_ledger():
    """Create a ProgressLedger instance."""
    return ProgressLedger()

@pytest.fixture
def sample_workflow():
    """Create a sample workflow for testing."""
    task1 = Task(name="task1", agent_type="test_agent", max_retries=1)
    task2 = Task(name="task2", agent_type="test_agent", max_retries=1)
    task3 = Task(name="task3", agent_type="test_agent", max_retries=1)
    
    step1 = WorkflowStep(task=task1, dependencies=[])
    step2 = WorkflowStep(task=task2, dependencies=["task1"])
    step3 = WorkflowStep(task=task3, dependencies=["task1", "task2"])
    
    return [step1, step2, step3]

@pytest.mark.asyncio
async def test_progress_ledger_register_workflow(progress_ledger, sample_workflow):
    """Test registering a workflow."""
    workflow_id = await progress_ledger.register_workflow("test_workflow", sample_workflow)
    
    assert workflow_id in progress_ledger.workflows
    assert len(progress_ledger.workflows[workflow_id]["steps"]) == 3
    assert progress_ledger.workflows[workflow_id]["status"] == "pending"
    assert isinstance(progress_ledger.workflows[workflow_id]["created_at"], datetime)

@pytest.mark.asyncio
async def test_progress_ledger_get_ready_steps(progress_ledger, sample_workflow):
    """Test getting ready steps from workflow."""
    workflow_id = await progress_ledger.register_workflow("test_workflow", sample_workflow)
    
    # Initially only task1 should be ready (no dependencies)
    ready_steps = progress_ledger.get_ready_steps(workflow_id)
    assert ready_steps == ["task1"]
    
    # Complete task1
    await progress_ledger.update_step_status(workflow_id, "task1", "completed")
    
    # Now task2 should be ready
    ready_steps = progress_ledger.get_ready_steps(workflow_id)
    assert ready_steps == ["task2"]
    
    # Complete task2
    await progress_ledger.update_step_status(workflow_id, "task2", "completed")
    
    # Finally task3 should be ready
    ready_steps = progress_ledger.get_ready_steps(workflow_id)
    assert ready_steps == ["task3"]

@pytest.mark.asyncio
async def test_progress_ledger_update_step_status(progress_ledger, sample_workflow):
    """Test updating step status."""
    workflow_id = await progress_ledger.register_workflow("test_workflow", sample_workflow)
    
    await progress_ledger.update_step_status(workflow_id, "task1", "completed")
    assert progress_ledger.workflows[workflow_id]["steps"]["task1"]["status"] == "completed"
    
    await progress_ledger.update_step_status(workflow_id, "task2", "failed")
    assert progress_ledger.workflows[workflow_id]["steps"]["task2"]["status"] == "failed"

@pytest.mark.asyncio
async def test_progress_ledger_invalid_workflow(progress_ledger, sample_workflow):
    """Test handling of invalid workflow operations."""
    # Try to get ready steps for nonexistent workflow
    with pytest.raises(KeyError):
        progress_ledger.get_ready_steps("nonexistent")
    
    # Try to update step in nonexistent workflow
    with pytest.raises(KeyError):
        await progress_ledger.update_step_status("nonexistent", "task1", "completed")
    
    # Register workflow and try to update nonexistent step
    workflow_id = await progress_ledger.register_workflow("test_workflow", sample_workflow)
    with pytest.raises(KeyError):
        await progress_ledger.update_step_status(workflow_id, "nonexistent", "completed")

@pytest.mark.asyncio
async def test_progress_ledger_workflow_completion(progress_ledger, sample_workflow):
    """Test workflow completion detection."""
    workflow_id = await progress_ledger.register_workflow("test_workflow", sample_workflow)
    
    # Complete all steps
    for step in sample_workflow:
        await progress_ledger.update_step_status(workflow_id, step.task.name, "completed")
    
    # Verify workflow is marked as completed
    assert progress_ledger.workflows[workflow_id]["status"] == "completed"
    assert isinstance(progress_ledger.workflows[workflow_id]["completed_at"], datetime) 