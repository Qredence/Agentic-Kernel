"""Tests for the Orchestrator agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.agents.orchestrator_agent import OrchestratorAgent
from agentic_kernel.ledgers.task_ledger import TaskLedger
from agentic_kernel.ledgers.progress_ledger import ProgressLedger
from agentic_kernel.types import Task, WorkflowStep
from agentic_kernel.config.agent_team import AgentConfig, LLMMapping

# --- Test Fixtures ---

@pytest.fixture
def mock_config():
    """Create a mock AgentConfig."""
    return MagicMock(spec=AgentConfig)

@pytest.fixture
def mock_task_ledger():
    """Create a mock TaskLedger with async methods."""
    ledger = AsyncMock(spec=TaskLedger)
    ledger.add_task = AsyncMock(return_value="task-123")
    ledger.update_task_result = AsyncMock()
    return ledger

@pytest.fixture
def mock_progress_ledger():
    """Create a mock ProgressLedger with async methods."""
    ledger = AsyncMock(spec=ProgressLedger)
    ledger.register_workflow = AsyncMock()
    ledger.update_step_status = AsyncMock()
    ledger.get_ready_steps = MagicMock(return_value=[])
    return ledger

@pytest.fixture
def mock_agent():
    """Create a mock BaseAgent."""
    agent = AsyncMock(spec=BaseAgent)
    agent.type = "test_agent"
    agent.execute = AsyncMock(return_value={"status": "success", "result": "test_result"})
    return agent

@pytest.fixture
def orchestrator(mock_config, mock_task_ledger, mock_progress_ledger):
    """Create an OrchestratorAgent instance with mock dependencies."""
    return OrchestratorAgent(mock_config, mock_task_ledger, mock_progress_ledger)

# --- Test Cases ---

def test_init(orchestrator, mock_config, mock_task_ledger, mock_progress_ledger):
    """Test OrchestratorAgent initialization."""
    assert orchestrator.config == mock_config
    assert orchestrator.task_ledger == mock_task_ledger
    assert orchestrator.progress_ledger == mock_progress_ledger
    assert orchestrator.agents == {}
    assert orchestrator.max_planning_attempts == 3
    assert orchestrator.max_inner_loop_iterations == 10
    assert orchestrator.reflection_threshold == 0.7

def test_register_agent(orchestrator, mock_agent):
    """Test agent registration."""
    orchestrator.register_agent(mock_agent)
    assert mock_agent.type in orchestrator.agents
    assert orchestrator.agents[mock_agent.type] == mock_agent

@pytest.mark.asyncio
async def test_execute_workflow_empty(orchestrator):
    """Test executing an empty workflow."""
    result = await orchestrator.execute_workflow([])
    assert result["status"] == "success"
    assert result["completed_steps"] == []
    assert result["failed_steps"] == []
    assert result["metrics"]["success_rate"] == 1.0

@pytest.mark.asyncio
async def test_execute_workflow_single_step(orchestrator, mock_agent):
    """Test executing a workflow with a single step."""
    # Register the mock agent
    orchestrator.register_agent(mock_agent)
    
    # Create a test task and workflow step
    task = Task(name="test_task", agent_type="test_agent", max_retries=1)
    workflow_step = WorkflowStep(task=task, dependencies=[])
    
    # Configure mock progress ledger to return our step as ready
    orchestrator.progress_ledger.get_ready_steps = MagicMock(return_value=["test_task"])
    
    # Execute the workflow
    result = await orchestrator.execute_workflow([workflow_step])
    
    # Verify the result
    assert result["status"] == "success"
    assert result["completed_steps"] == ["test_task"]
    assert result["failed_steps"] == []
    assert result["metrics"]["success_rate"] == 1.0
    
    # Verify interactions with dependencies
    orchestrator.progress_ledger.register_workflow.assert_called_once()
    orchestrator.task_ledger.add_task.assert_called_once_with(task)
    mock_agent.execute.assert_called_once_with(task)

@pytest.mark.asyncio
async def test_execute_workflow_with_failure(orchestrator, mock_agent):
    """Test workflow execution with a failing step."""
    # Configure agent to fail
    mock_agent.execute = AsyncMock(side_effect=Exception("Test failure"))
    orchestrator.register_agent(mock_agent)
    
    # Create test task and workflow step
    task = Task(name="failing_task", agent_type="test_agent", max_retries=0)
    workflow_step = WorkflowStep(task=task, dependencies=[])
    
    # Configure mock progress ledger
    orchestrator.progress_ledger.get_ready_steps = MagicMock(return_value=["failing_task"])
    
    # Execute workflow
    result = await orchestrator.execute_workflow([workflow_step])
    
    # Verify failure handling
    assert result["status"] == "partial_success"
    assert result["completed_steps"] == []
    assert result["failed_steps"] == ["failing_task"]
    assert result["metrics"]["success_rate"] == 0.0

@pytest.mark.asyncio
async def test_execute_workflow_with_retry(orchestrator, mock_agent):
    """Test workflow execution with retry logic."""
    # Configure agent to fail once then succeed
    mock_agent.execute = AsyncMock(side_effect=[Exception("First attempt"), {"status": "success", "result": "retry_success"}])
    orchestrator.register_agent(mock_agent)
    
    # Create test task with retry
    task = Task(name="retry_task", agent_type="test_agent", max_retries=1)
    workflow_step = WorkflowStep(task=task, dependencies=[])
    
    # Configure mock progress ledger
    orchestrator.progress_ledger.get_ready_steps = MagicMock(return_value=["retry_task"])
    
    # Execute workflow
    result = await orchestrator.execute_workflow([workflow_step])
    
    # Verify retry succeeded
    assert result["status"] == "success"
    assert result["completed_steps"] == ["retry_task"]
    assert result["failed_steps"] == []
    assert "retry_task" in result["retried_steps"]
    assert mock_agent.execute.call_count == 2

@pytest.mark.parametrize(
    "workflow_steps,completed,failed,expected_progress",
    [
        ([], [], [], 1.0),  # Empty workflow
        (["step1"], [], [], 0.0),  # No progress
        (["step1"], ["step1"], [], 1.0),  # Complete
        (["step1", "step2"], ["step1"], [], 0.5),  # Half complete
        (["step1", "step2"], ["step1"], ["step2"], 1.0),  # Complete with failure
    ]
)
def test_calculate_progress(orchestrator, workflow_steps, completed, failed, expected_progress):
    """Test progress calculation with various scenarios."""
    # Create workflow steps
    workflow = []
    for name in workflow_steps:
        task = Task(name=name, agent_type="test_agent", max_retries=0)
        workflow.append(WorkflowStep(task=task, dependencies=[]))
    
    progress = orchestrator._calculate_progress(workflow, completed, failed)
    assert progress == pytest.approx(expected_progress)
