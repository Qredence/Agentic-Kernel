"""Tests for the TaskLedger and ProgressLedger classes."""

import pytest
from datetime import datetime, timedelta
from agentic_kernel.ledgers import TaskLedger, ProgressLedger, TaskEntry, ProgressEntry


@pytest.fixture
def task_ledger():
    return TaskLedger()


@pytest.fixture
def progress_ledger():
    return ProgressLedger()


def test_task_ledger_add_task(task_ledger):
    """Test adding a task to the ledger."""
    task_id = task_ledger.add_task(
        description="Test task",
        assigned_agent="TestAgent",
        dependencies=["task_1"],
        metadata={"priority": "high"}
    )
    
    assert task_id == "task_1"
    task = task_ledger.get_task(task_id)
    assert task.description == "Test task"
    assert task.assigned_agent == "TestAgent"
    assert task.dependencies == ["task_1"]
    assert task.metadata == {"priority": "high"}
    assert isinstance(task.created_at, datetime)


def test_task_ledger_update_task(task_ledger):
    """Test updating a task in the ledger."""
    task_id = task_ledger.add_task(
        description="Original task",
        assigned_agent="TestAgent"
    )
    
    success = task_ledger.update_task(
        task_id,
        description="Updated task",
        metadata={"status": "in_progress"}
    )
    
    assert success is True
    task = task_ledger.get_task(task_id)
    assert task.description == "Updated task"
    assert task.metadata == {"status": "in_progress"}


def test_task_ledger_get_dependent_tasks(task_ledger):
    """Test retrieving dependent tasks."""
    task1_id = task_ledger.add_task(
        description="Task 1",
        assigned_agent="TestAgent"
    )
    task2_id = task_ledger.add_task(
        description="Task 2",
        assigned_agent="TestAgent",
        dependencies=[task1_id]
    )
    
    dependents = task_ledger.get_dependent_tasks(task1_id)
    assert len(dependents) == 1
    assert dependents[0].id == task2_id


def test_progress_ledger_record_progress(progress_ledger):
    """Test recording progress for a task."""
    progress_ledger.record_progress(
        task_id="task_1",
        result={"output": "test"},
        status="in_progress",
        metrics={"duration": 1.5}
    )
    
    entry = progress_ledger.get_progress("task_1")
    assert entry.status == "in_progress"
    assert entry.result == {"output": "test"}
    assert entry.metrics == {"duration": 1.5}
    assert entry.started_at is not None
    assert entry.completed_at is None


def test_progress_ledger_update_progress(progress_ledger):
    """Test updating progress for a task."""
    # Initial progress
    progress_ledger.record_progress(
        task_id="task_1",
        status="in_progress"
    )
    
    # Update progress
    progress_ledger.record_progress(
        task_id="task_1",
        status="completed",
        result={"output": "success"},
        metrics={"duration": 2.0}
    )
    
    entry = progress_ledger.get_progress("task_1")
    assert entry.status == "completed"
    assert entry.result == {"output": "success"}
    assert entry.metrics == {"duration": 2.0}
    assert entry.completed_at is not None


def test_progress_ledger_success_rate(progress_ledger):
    """Test calculating success rate."""
    # Add some tasks with different statuses
    progress_ledger.record_progress("task_1", status="completed")
    progress_ledger.record_progress("task_2", status="failed")
    progress_ledger.record_progress("task_3", status="completed")
    
    assert progress_ledger.get_success_rate() == 2/3


def test_progress_ledger_get_failed_tasks(progress_ledger):
    """Test retrieving failed tasks."""
    progress_ledger.record_progress("task_1", status="completed")
    progress_ledger.record_progress("task_2", status="failed", error="Error message")
    progress_ledger.record_progress("task_3", status="failed", error="Another error")
    
    failed_tasks = progress_ledger.get_failed_tasks()
    assert len(failed_tasks) == 2
    assert all(task.status == "failed" for task in failed_tasks)
    assert all(task.error is not None for task in failed_tasks)


def test_progress_ledger_metrics_summary(progress_ledger):
    """Test generating metrics summary."""
    progress_ledger.record_progress(
        "task_1",
        metrics={"duration": 1.0, "memory": 100}
    )
    progress_ledger.record_progress(
        "task_2",
        metrics={"duration": 2.0, "memory": 200}
    )
    
    summary = progress_ledger.get_metrics_summary()
    
    assert "duration" in summary
    assert summary["duration"]["average"] == 1.5
    assert summary["duration"]["min"] == 1.0
    assert summary["duration"]["max"] == 2.0
    
    assert "memory" in summary
    assert summary["memory"]["average"] == 150
    assert summary["memory"]["min"] == 100
    assert summary["memory"]["max"] == 200


def test_task_entry_defaults():
    """Test TaskEntry default values."""
    task = TaskEntry(
        id="task_1",
        description="Test task",
        assigned_agent="TestAgent"
    )
    
    assert isinstance(task.created_at, datetime)
    assert task.dependencies == []
    assert task.metadata == {}


def test_progress_entry_defaults():
    """Test ProgressEntry default values."""
    entry = ProgressEntry(
        task_id="task_1",
        status="pending"
    )
    
    assert entry.result is None
    assert entry.started_at is None
    assert entry.completed_at is None
    assert entry.error is None
    assert entry.metrics == {} 