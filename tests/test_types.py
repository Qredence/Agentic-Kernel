"""Tests for core types (Task and WorkflowStep)."""

import pytest
from agentic_kernel.types import Task, WorkflowStep

def test_task_creation():
    """Test Task creation with basic attributes."""
    task = Task(
        name="test_task",
        agent_type="test_agent",
        max_retries=2
    )
    
    assert task.name == "test_task"
    assert task.agent_type == "test_agent"
    assert task.max_retries == 2

def test_task_with_optional_fields():
    """Test Task creation with optional fields."""
    task = Task(
        name="test_task",
        agent_type="test_agent",
        max_retries=2,
        description="Test description",
        metadata={"key": "value"},
        timeout=30
    )
    
    assert task.description == "Test description"
    assert task.metadata == {"key": "value"}
    assert task.timeout == 30

def test_workflow_step_creation():
    """Test WorkflowStep creation with basic attributes."""
    task = Task(name="test_task", agent_type="test_agent", max_retries=1)
    step = WorkflowStep(task=task, dependencies=[])
    
    assert step.task == task
    assert step.dependencies == []

def test_workflow_step_with_dependencies():
    """Test WorkflowStep creation with dependencies."""
    task1 = Task(name="task1", agent_type="test_agent", max_retries=1)
    task2 = Task(name="task2", agent_type="test_agent", max_retries=1)
    task3 = Task(name="task3", agent_type="test_agent", max_retries=1)
    
    step1 = WorkflowStep(task=task1, dependencies=[])
    step2 = WorkflowStep(task=task2, dependencies=[])
    step3 = WorkflowStep(task=task3, dependencies=["task1", "task2"])
    
    assert step3.dependencies == ["task1", "task2"]

@pytest.mark.parametrize(
    "name,agent_type,max_retries,should_raise",
    [
        ("", "agent", 1, True),  # Empty name
        ("task", "", 1, True),   # Empty agent_type
        ("task", "agent", -1, True),  # Negative retries
        ("task", "agent", 1, False),  # Valid case
    ]
)
def test_task_validation(name, agent_type, max_retries, should_raise):
    """Test Task validation for various invalid inputs."""
    if should_raise:
        with pytest.raises(ValueError):
            Task(name=name, agent_type=agent_type, max_retries=max_retries)
    else:
        task = Task(name=name, agent_type=agent_type, max_retries=max_retries)
        assert task.name == name
        assert task.agent_type == agent_type
        assert task.max_retries == max_retries

@pytest.mark.parametrize(
    "dependencies,should_raise",
    [
        (None, True),  # None dependencies
        ([""], True),  # Empty dependency name
        ([123], True),  # Non-string dependency
        (["task1", "task1"], True),  # Duplicate dependencies
        (["task1", "task2"], False),  # Valid case
    ]
)
def test_workflow_step_validation(dependencies, should_raise):
    """Test WorkflowStep validation for various invalid inputs."""
    task = Task(name="test_task", agent_type="test_agent", max_retries=1)
    
    if should_raise:
        with pytest.raises((ValueError, TypeError)):
            WorkflowStep(task=task, dependencies=dependencies)
    else:
        step = WorkflowStep(task=task, dependencies=dependencies)
        assert step.task == task
        assert step.dependencies == dependencies

def test_task_equality():
    """Test Task equality comparison."""
    task1 = Task(name="task", agent_type="agent", max_retries=1)
    task2 = Task(name="task", agent_type="agent", max_retries=1)
    task3 = Task(name="different", agent_type="agent", max_retries=1)
    
    assert task1 == task2
    assert task1 != task3
    assert task1 != "not_a_task"

def test_workflow_step_equality():
    """Test WorkflowStep equality comparison."""
    task1 = Task(name="task", agent_type="agent", max_retries=1)
    task2 = Task(name="task", agent_type="agent", max_retries=1)
    
    step1 = WorkflowStep(task=task1, dependencies=["dep1"])
    step2 = WorkflowStep(task=task2, dependencies=["dep1"])
    step3 = WorkflowStep(task=task1, dependencies=["dep2"])
    
    assert step1 == step2  # Same task (by value) and dependencies
    assert step1 != step3  # Same task but different dependencies
    assert step1 != "not_a_step" 