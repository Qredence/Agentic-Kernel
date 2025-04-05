"""End-to-end workflow tests for the Agentic-Kernel system."""

import pytest
import asyncio
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

from agentic_kernel.agents import (
    CoderAgent,
    TerminalAgent,
    FileSurferAgent,
    WebSurferAgent,
)
from agentic_kernel.orchestrator import OrchestratorAgent
from agentic_kernel.config import AgentConfig, LLMMapping  # Simple AgentConfig for single agents
from agentic_kernel.ledgers import TaskLedger, ProgressLedger
from agentic_kernel.types import Task, WorkflowStep

@pytest.fixture
async def agent_config():
    """Create a test agent configuration."""
    return AgentConfig(
        name="test_config",
        type="test_agent",
        description="A test agent for workflow execution",
        llm_mapping=LLMMapping(
            model="gpt-4",
            temperature=0.7,
            max_tokens=2000
        )
    )

@pytest.fixture
async def mock_agents(agent_config):
    """Create mock agents for testing."""
    coder = CoderAgent(config=agent_config)
    terminal = TerminalAgent(config=agent_config)
    file_surfer = FileSurferAgent(config=agent_config)
    web_surfer = WebSurferAgent(config=agent_config)
    
    # Mock the execute methods
    coder.execute = AsyncMock(return_value={"status": "success", "result": "Code generated"})
    terminal.execute = AsyncMock(return_value={"status": "success", "result": "Command executed"})
    file_surfer.execute = AsyncMock(return_value={"status": "success", "result": "File processed"})
    web_surfer.execute = AsyncMock(return_value={"status": "success", "result": "Web content fetched"})
    
    # Set agent types
    coder.type = "coder"
    terminal.type = "terminal"
    file_surfer.type = "file_surfer"
    web_surfer.type = "web_surfer"
    
    return {
        "coder": coder,
        "terminal": terminal,
        "file_surfer": file_surfer,
        "web_surfer": web_surfer
    }

@pytest.fixture
async def orchestrator(agent_config, mock_agents):
    """Create an orchestrator instance with mock agents."""
    task_ledger = TaskLedger(goal="Test workflow execution")
    progress_ledger = ProgressLedger(task_id="test_task")
    
    orchestrator = OrchestratorAgent(
        config=agent_config,
        task_ledger=task_ledger,
        progress_ledger=progress_ledger
    )
    
    # Register mock agents
    for agent in mock_agents.values():
        orchestrator.register_agent(agent)
    
    return orchestrator

@pytest.mark.asyncio
async def test_simple_workflow_execution(orchestrator, mock_agents):
    """Test execution of a simple workflow involving multiple agents."""
    # Define a simple workflow
    workflow = [
        WorkflowStep(
            task=Task(
                name="fetch_web_content",
                description="Fetch content from a URL",
                agent_type="web_surfer",
                parameters={"url": "https://example.com"}
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="process_content",
                description="Process the fetched content",
                agent_type="coder",
                parameters={"content": "Sample content"}
            ),
            dependencies=["fetch_web_content"]
        )
    ]
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify execution
    assert result["status"] == "success"
    assert len(result["completed_steps"]) == 2
    assert mock_agents["web_surfer"].execute.called
    assert mock_agents["coder"].execute.called

@pytest.mark.asyncio
async def test_parallel_workflow_execution(orchestrator, mock_agents):
    """Test execution of parallel workflow steps."""
    # Define a workflow with parallel steps
    workflow = [
        WorkflowStep(
            task=Task(
                name="fetch_file_1",
                description="Process first file",
                agent_type="file_surfer",
                parameters={"path": "file1.txt"}
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="fetch_file_2",
                description="Process second file",
                agent_type="file_surfer",
                parameters={"path": "file2.txt"}
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="combine_results",
                description="Combine processed files",
                agent_type="coder",
                parameters={"files": ["file1.txt", "file2.txt"]}
            ),
            dependencies=["fetch_file_1", "fetch_file_2"]
        )
    ]
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify execution
    assert result["status"] == "success"
    assert len(result["completed_steps"]) == 3
    assert mock_agents["file_surfer"].execute.call_count == 2
    assert mock_agents["coder"].execute.called

@pytest.mark.asyncio
async def test_error_handling_and_recovery(orchestrator, mock_agents):
    """Test workflow error handling and recovery mechanisms."""
    # Mock an error in one agent
    mock_agents["terminal"].execute = AsyncMock(
        side_effect=[Exception("Command failed"), {"status": "success", "result": "Retry succeeded"}]
    )
    
    workflow = [
        WorkflowStep(
            task=Task(
                name="run_command",
                description="Run a terminal command",
                agent_type="terminal",
                parameters={"command": "echo test"},
                max_retries=1
            ),
            dependencies=[]
        )
    ]
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify error handling
    assert result["status"] == "success"
    assert mock_agents["terminal"].execute.call_count == 2
    assert len(result["retried_steps"]) == 1

@pytest.mark.asyncio
async def test_workflow_metrics_collection(orchestrator, mock_agents):
    """Test collection and reporting of workflow metrics."""
    workflow = [
        WorkflowStep(
            task=Task(
                name="test_task",
                description="Test metrics collection",
                agent_type="coder",
                parameters={}
            ),
            dependencies=[]
        )
    ]
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify metrics
    assert "metrics" in result
    assert "execution_time" in result["metrics"]
    assert "resource_usage" in result["metrics"]
    assert "success_rate" in result["metrics"] 