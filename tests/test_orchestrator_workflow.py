"""Tests for the Orchestrator's workflow execution logic."""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any
from datetime import datetime

from agentic_kernel.agents.orchestrator_agent import OrchestratorAgent
from agentic_kernel.ledgers import TaskLedger, ProgressLedger, PlanStep


@pytest.fixture
def mock_llm():
    mock = AsyncMock()
    # Make evaluate_progress awaitable
    mock.evaluate_progress = AsyncMock(return_value={
        "success_rate": 0.9,
        "needs_replanning": False,
        "suggestions": []
    })
    # Make replan_task awaitable
    mock.replan_task = AsyncMock(return_value=[
        PlanStep(
            description="Alternative step",
            status="pending",
            depends_on=[]
        )
    ])
    return mock


@pytest.fixture
def mock_agents():
    agents = {}
    for name in ["WebSurferAgent", "FileSurferAgent", "CoderAgent", "TerminalAgent"]:
        mock_agent = AsyncMock()
        mock_agent.__class__.__name__ = name
        mock_agent.execute_task = AsyncMock(return_value={"status": "success", "output": "Task completed"})
        agents[name] = mock_agent
    return agents


@pytest.fixture
def orchestrator_agent(mock_llm, mock_agents):
    agent = OrchestratorAgent(
        name="test_orchestrator",
        description="Test orchestrator agent",
        llm=mock_llm,
        config={
            "max_planning_attempts": 3,
            "reflection_threshold": 0.7,
            "max_task_retries": 2
        }
    )
    for name, mock_agent in mock_agents.items():
        agent.register_agent(mock_agent)
    return agent


@pytest.fixture
def task_ledger():
    return TaskLedger(
        goal="Test workflow execution",
        initial_facts=["Initial context"],
        assumptions=["Test assumption"]
    )


@pytest.fixture
def progress_ledger():
    return ProgressLedger(
        task_id="test_task",
        current_status="not_started"
    )


async def test_outer_loop_execution(orchestrator_agent, mock_llm, task_ledger, progress_ledger):
    """Test the complete outer loop execution flow."""
    # Mock the initial plan
    steps = [
        PlanStep(
            step_id="1",
            description="Research API documentation",
            status="pending",
            depends_on=[]
        ),
        PlanStep(
            step_id="2",
            description="Analyze existing codebase",
            status="pending",
            depends_on=[]
        ),
        PlanStep(
            step_id="3",
            description="Generate implementation",
            status="pending",
            depends_on=[]
        )
    ]
    task_ledger.plan = steps
    
    # Mock successful execution for WebSurferAgent
    mock_llm.evaluate_progress.return_value = {
        "success_rate": 0.9,
        "needs_replanning": False,
        "suggestions": []
    }
    
    result = await orchestrator_agent.execute_workflow(
        task_ledger,
        progress_ledger
    )
    
    assert result["status"] == "success"
    assert len(result["completed_steps"]) == 3
    assert result["success_rate"] > 0.8


async def test_outer_loop_replanning(orchestrator_agent, mock_llm, task_ledger, progress_ledger):
    """Test replanning when a step fails."""
    # Initial plan
    steps = [
        PlanStep(
            step_id="1",
            description="Research API documentation",
            status="pending",
            depends_on=[]
        )
    ]
    task_ledger.plan = steps
    
    # Mock failed execution then success
    mock_llm.evaluate_progress.side_effect = [
        {
            "success_rate": 0.3,
            "needs_replanning": True,
            "suggestions": ["Consider alternative approach"]
        },
        {
            "success_rate": 0.9,
            "needs_replanning": False,
            "suggestions": []
        }
    ]
    
    # Mock replan
    new_steps = [
        PlanStep(
            step_id="2",
            description="Use local documentation",
            status="pending",
            depends_on=[]
        )
    ]
    mock_llm.replan_task.return_value = new_steps
    
    result = await orchestrator_agent.execute_workflow(
        task_ledger,
        progress_ledger
    )
    
    assert result["status"] == "success"
    assert len(result["replanning_events"]) == 1
    mock_llm.replan_task.assert_called_once()


async def test_outer_loop_task_retry(orchestrator_agent, mock_llm, task_ledger, progress_ledger):
    """Test retrying a failed task."""
    # Mock plan
    steps = [
        PlanStep(
            step_id="1",
            description="Execute database migration",
            status="pending",
            depends_on=[]
        )
    ]
    task_ledger.plan = steps
    
    # Mock failed execution then success
    orchestrator_agent.available_agents["TerminalAgent"].execute_task.side_effect = [
        {"status": "error", "error": "Connection failed"},
        {"status": "success", "output": "Migration completed"}
    ]
    
    result = await orchestrator_agent.execute_workflow(
        task_ledger,
        progress_ledger
    )
    
    assert result["status"] == "success"
    assert result["retry_count"] == 1
    assert len(result["completed_steps"]) == 1


async def test_outer_loop_parallel_execution(orchestrator_agent, mock_llm, task_ledger, progress_ledger):
    """Test executing independent tasks in parallel."""
    # Mock plan with parallel tasks
    steps = [
        PlanStep(
            step_id="1",
            description="Research API documentation",
            status="pending",
            depends_on=[]
        ),
        PlanStep(
            step_id="2",
            description="Analyze codebase",
            status="pending",
            depends_on=[]
        ),
        PlanStep(
            step_id="3",
            description="Generate implementation",
            status="pending",
            depends_on=["1", "2"]  # Using step_ids from previous steps
        )
    ]
    task_ledger.plan = steps
    
    result = await orchestrator_agent.execute_workflow(
        task_ledger,
        progress_ledger,
        allow_parallel=True
    )
    
    assert result["status"] == "success"
    assert result["parallel_executions"] > 0


async def test_outer_loop_error_handling(orchestrator_agent, mock_llm, task_ledger, progress_ledger):
    """Test handling various error conditions in the outer loop."""
    # Mock plan with a step to trigger progress evaluation
    steps = [
        PlanStep(
            step_id="1",
            description="Step that will fail",
            status="pending",
            depends_on=[]
        )
    ]
    task_ledger.plan = steps
    
    # Mock planning failure
    mock_llm.evaluate_progress.side_effect = Exception("Planning failed")
    
    result = await orchestrator_agent.execute_workflow(
        task_ledger,
        progress_ledger
    )
    
    assert result["status"] == "error"
    assert "Planning failed" in str(result.get("error", ""))


@pytest.mark.asyncio
async def test_outer_loop_progress_tracking(orchestrator_agent, mock_llm, mock_agents, task_ledger, progress_ledger):
    """Test that the outer loop properly tracks progress and metrics."""
    # Setup mock plan
    steps = [
        PlanStep(
            step_id="1",
            description="Research API documentation",
            status="pending",
            depends_on=[]
        ),
        PlanStep(
            step_id="2",
            description="Analyze codebase",
            status="pending",
            depends_on=[]
        )
    ]
    task_ledger.plan = steps
    
    # Setup mock agent responses with metrics
    mock_metrics = {
        "cpu_usage": 50.0,
        "memory_usage": 100.0,
        "duration": 1.0
    }
    
    for agent in mock_agents.values():
        agent.execute_task.return_value = {
            "status": "success",
            "output": "Step completed",
            "metrics": mock_metrics
        }
    
    # Setup mock LLM responses
    mock_llm.evaluate_progress.return_value = {
        "needs_replanning": False,
        "success_rate": 1.0,
        "suggestions": []
    }
    
    # Execute workflow
    result = await orchestrator_agent.execute_workflow(task_ledger, progress_ledger)
    
    # Verify metrics are collected and aggregated
    assert result["status"] == "success"
    assert "metrics" in result
    assert result["metrics"]["cpu_usage"] == 50.0
    assert result["metrics"]["memory_usage"] == 100.0
    assert result["metrics"]["duration"] > 0
    assert result["success_rate"] == 1.0
    assert len(result["completed_steps"]) == 2
    assert result["retry_count"] == 0
    assert len(result["replanning_events"]) == 0 