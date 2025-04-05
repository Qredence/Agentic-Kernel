import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from agentic_kernel.agents.orchestrator_agent import OrchestratorAgent
from agentic_kernel.ledgers import TaskLedger, ProgressLedger

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
            "reflection_threshold": 0.7
        }
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

async def test_task_planning(orchestrator_agent, mock_llm, task_ledger):
    """Test that the orchestrator can create a task plan."""
    mock_llm.plan_task.return_value = {
        "steps": [
            {"id": 1, "description": "Research task requirements", "agent": "WebSurferAgent"},
            {"id": 2, "description": "Analyze existing codebase", "agent": "FileSurferAgent"},
            {"id": 3, "description": "Generate implementation plan", "agent": "CoderAgent"}
        ]
    }
    
    task_description = "Implement a new feature for user authentication"
    plan = await orchestrator_agent.plan_task(task_description, task_ledger)
    
    assert len(plan["steps"]) == 3
    assert plan["steps"][0]["agent"] == "WebSurferAgent"
    mock_llm.plan_task.assert_called_once_with(task_description)

async def test_task_delegation(orchestrator_agent, mock_llm):
    """Test that the orchestrator can delegate tasks to appropriate agents."""
    mock_agents = {
        "WebSurferAgent": Mock(),
        "FileSurferAgent": Mock(),
        "CoderAgent": Mock()
    }
    orchestrator_agent.available_agents = mock_agents
    
    task = {
        "id": 1,
        "description": "Research authentication best practices",
        "agent": "WebSurferAgent"
    }
    
    await orchestrator_agent.delegate_task(task)
    mock_agents["WebSurferAgent"].execute_task.assert_called_once()

async def test_reflection_and_replanning(orchestrator_agent, mock_llm, progress_ledger):
    """Test that the orchestrator can reflect on progress and replan if needed."""
    mock_llm.evaluate_progress.return_value = {
        "success_rate": 0.5,
        "needs_replanning": True,
        "suggestions": ["Consider alternative approach"]
    }
    
    evaluation = await orchestrator_agent.reflect_on_progress(progress_ledger)
    
    assert evaluation["needs_replanning"] is True
    assert len(evaluation["suggestions"]) > 0
    mock_llm.evaluate_progress.assert_called_once()

async def test_error_handling(orchestrator_agent):
    """Test that the orchestrator handles errors appropriately."""
    with pytest.raises(ValueError):
        await orchestrator_agent.execute_task("", None)  # Empty task description
    
    with pytest.raises(ValueError):
        await orchestrator_agent.delegate_task(None)  # Invalid task 