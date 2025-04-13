"""Tests for the OrchestratorAgent class."""

from unittest.mock import MagicMock, Mock

import pytest

from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.agents.orchestrator_agent import OrchestratorAgent
from agentic_kernel.ledgers.progress_ledger import ProgressLedger
from agentic_kernel.ledgers.task_ledger import TaskLedger
from agentic_kernel.types import Task, WorkflowStep


@pytest.fixture
def mock_llm():
    return Mock()


@pytest.fixture
def orchestrator_agent(mock_llm):
    return OrchestratorAgent(
        name="test_orchestrator",
        description="Test orchestrator agent",
        llm=mock_llm,
        config={
            "max_planning_attempts": 3,
            "reflection_threshold": 0.7,
        },
    )


@pytest.fixture
def task_ledger():
    return TaskLedger()


@pytest.fixture
def progress_ledger():
    return ProgressLedger()


async def test_orchestrator_initialization(orchestrator_agent):
    """Test that the orchestrator agent is initialized correctly."""
    assert orchestrator_agent.name == "test_orchestrator"
    assert orchestrator_agent.description == "Test orchestrator agent"
    assert orchestrator_agent.config["max_planning_attempts"] == 3
    assert orchestrator_agent.config["reflection_threshold"] == 0.7


async def test_task_planning(orchestrator_agent, mock_llm):
    """Test that the orchestrator can create a task plan."""
    mock_llm.plan_task.return_value = {
        "steps": [
            {
                "id": 1,
                "description": "Research task requirements",
                "agent": "WebSurferAgent",
            },
            {
                "id": 2,
                "description": "Analyze existing codebase",
                "agent": "FileSurferAgent",
            },
            {
                "id": 3,
                "description": "Generate implementation plan",
                "agent": "CoderAgent",
            },
        ],
    }

    task = Task(
        name="test_task",
        agent_type="TestAgent",
        parameters={},
    )
    plan = await orchestrator_agent.plan_task(task)
    assert len(plan["steps"]) == 3
    assert plan["steps"][0]["agent"] == "WebSurferAgent"


async def test_invalid_task_delegation(orchestrator_agent):
    """Test that invalid task delegation raises appropriate errors."""
    with pytest.raises(ValueError, match="Task cannot be None"):
        await orchestrator_agent.delegate_task(None)


async def test_agent_registration(orchestrator_agent):
    """Test that agents can be registered with the orchestrator."""
    mock_agent = MagicMock(spec=BaseAgent)
    mock_agent.agent_id = "agent_1"
    mock_agent.type = "TestAgent"

    orchestrator_agent.register_agent(mock_agent)
    assert "agent_1" in orchestrator_agent.agents
    assert orchestrator_agent.agents["agent_1"].type == "TestAgent"


async def test_agent_selection(orchestrator_agent):
    """Test that the orchestrator can select the best agent for a task."""
    mock_agent = MagicMock(spec=BaseAgent)
    mock_agent.agent_id = "agent_1"
    mock_agent.type = "TestAgent"
    orchestrator_agent.register_agent(mock_agent)

    task = Task(
        name="test_task",
        agent_type="TestAgent",
        parameters={},
    )
    selected_agent = await orchestrator_agent.select_agent_for_task(task)

    assert selected_agent is not None
    assert selected_agent.agent_id == "agent_1"


async def test_workflow_creation(orchestrator_agent):
    """Test that a workflow can be created and tracked."""
    steps = [
        WorkflowStep(
            task=Task(
                name="step_1",
                agent_type="TestAgent",
                parameters={},
            ),
        ),
    ]
    workflow_id = await orchestrator_agent.create_workflow(
        name="test_workflow",
        description="A test workflow",
        steps=steps,
    )

    assert workflow_id is not None
    assert orchestrator_agent.workflow_history.get_workflow(workflow_id) is not None


async def test_task_delegation(orchestrator_agent):
    """Test that the orchestrator can delegate tasks to appropriate agents."""
    mock_agents = {
        "WebSurferAgent": Mock(),
        "FileSurferAgent": Mock(),
        "CoderAgent": Mock(),
    }
    orchestrator_agent.available_agents = mock_agents

    task = {
        "id": 1,
        "description": "Research authentication best practices",
        "agent": "WebSurferAgent",
    }

    await orchestrator_agent.delegate_task(task)
    mock_agents["WebSurferAgent"].execute_task.assert_called_once()


async def test_reflection_and_replanning(orchestrator_agent, mock_llm, progress_ledger):
    """Test that the orchestrator can reflect on progress and replan if needed."""
    mock_llm.evaluate_progress.return_value = {
        "success_rate": 0.5,
        "needs_replanning": True,
        "suggestions": ["Consider alternative approach"],
    }

    evaluation = await orchestrator_agent.reflect_on_progress(progress_ledger)

    assert evaluation["needs_replanning"] is True
    assert len(evaluation["suggestions"]) > 0
    mock_llm.evaluate_progress.assert_called_once()


async def test_error_handling(orchestrator_agent):
    """Test that the orchestrator handles errors appropriately."""
    with pytest.raises(ValueError, match="Task description cannot be empty"):
        await orchestrator_agent.execute_task("", None)  # Empty task description

    with pytest.raises(ValueError, match="Task cannot be None"):
        await orchestrator_agent.delegate_task(None)  # Invalid task
