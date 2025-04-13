"""Tests for the WorkflowManager class."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agentic_kernel.agents.base import BaseAgent
from src.agentic_kernel.communication.dynamic_capability_registry import (
    DynamicCapabilityRegistry,
)
from src.agentic_kernel.orchestrator.workflow_manager import (
    WorkflowManager,
    WorkflowTemplate,
)
from src.agentic_kernel.types import Task, WorkflowStep


@pytest.fixture
def mock_capability_registry():
    """Create a mock DynamicCapabilityRegistry."""
    registry = AsyncMock(spec=DynamicCapabilityRegistry)
    registry.register_agent = AsyncMock()
    registry.discover_capabilities = AsyncMock(return_value=[])
    return registry


@pytest.fixture
def mock_agent():
    """Create a mock BaseAgent."""
    agent = AsyncMock(spec=BaseAgent)
    agent.agent_id = "test_agent_id"
    agent.type = "test_agent_type"
    agent.get_resources = MagicMock(return_value={"memory": 100, "cpu": 50})
    agent.get_metadata = MagicMock(return_value={"version": "1.0"})
    agent.execute = AsyncMock(return_value={"status": "success", "result": "test_result"})
    return agent


@pytest.fixture
def workflow_manager(mock_capability_registry, tmp_path):
    """Create a WorkflowManager instance with mock dependencies."""
    persistence_path = os.path.join(tmp_path, "workflow_data")
    return WorkflowManager(
        capability_registry=mock_capability_registry,
        persistence_path=persistence_path,
    )


@pytest.fixture
def workflow_template():
    """Create a sample workflow template."""
    return WorkflowTemplate(
        name="Test Template",
        description="A test workflow template",
        parameters={
            "url": {
                "type": "string",
                "description": "API URL",
                "required": True,
            },
            "format": {
                "type": "string",
                "description": "Output format",
                "default": "json",
            },
        },
        steps=[
            {
                "name": "fetch_data",
                "description": "Fetch data from API",
                "agent_type": "web_surfer",
                "parameters": {
                    "url": "${url}",
                },
            },
            {
                "name": "process_data",
                "description": "Process the fetched data",
                "agent_type": "data_processor",
                "parameters": {
                    "format": "${format}",
                },
                "dependencies": ["fetch_data"],
            },
        ],
    )


@pytest.fixture
def sample_workflow_steps():
    """Create sample workflow steps."""
    return [
        WorkflowStep(
            task=Task(
                name="step1",
                description="First step",
                agent_type="test_agent_type",
                parameters={"param1": "value1"},
            ),
            dependencies=[],
        ),
        WorkflowStep(
            task=Task(
                name="step2",
                description="Second step",
                agent_type="test_agent_type",
                parameters={"param2": "value2"},
            ),
            dependencies=["step1"],
        ),
    ]


@pytest.mark.asyncio
async def test_register_agent(workflow_manager, mock_agent, mock_capability_registry):
    """Test registering an agent with the workflow manager."""
    await workflow_manager.register_agent(mock_agent)
    
    # Verify agent was registered
    assert mock_agent.agent_id in workflow_manager.agents
    assert workflow_manager.agents[mock_agent.agent_id] == mock_agent
    
    # Verify agent was registered with capability registry
    mock_capability_registry.register_agent.assert_called_once()
    
    # Verify agent was registered with metrics collector
    assert mock_agent.agent_id in workflow_manager.metrics_collector.agent_metrics


@pytest.mark.asyncio
async def test_discover_agents(workflow_manager, mock_capability_registry):
    """Test discovering agents with specific capabilities."""
    # Configure mock to return some agents
    mock_capability_registry.discover_capabilities.return_value = [
        {"agent_id": "agent1", "agent_type": "web_surfer", "capabilities": ["web_search"]},
        {"agent_id": "agent2", "agent_type": "data_processor", "capabilities": ["data_processing"]},
    ]
    
    # Discover agents
    agents = await workflow_manager.discover_agents(capability_types=["web_search"])
    
    # Verify discovery was called with correct parameters
    mock_capability_registry.discover_capabilities.assert_called_once_with(
        requester_id="workflow_manager",
        capability_types=["web_search"],
        detail_level="detailed",
    )
    
    # Verify returned agents
    assert len(agents) == 2
    assert agents[0]["agent_id"] == "agent1"
    assert agents[1]["agent_id"] == "agent2"


@pytest.mark.asyncio
async def test_register_workflow_template(workflow_manager, workflow_template):
    """Test registering a workflow template."""
    template_id = await workflow_manager.register_workflow_template(workflow_template)
    
    # Verify template was registered
    assert template_id in workflow_manager.templates
    assert workflow_manager.templates[template_id] == workflow_template
    
    # Verify template ID was returned
    assert template_id == workflow_template.template_id


@pytest.mark.asyncio
async def test_create_workflow_from_template(workflow_manager, workflow_template):
    """Test creating a workflow from a template."""
    # Register the template
    template_id = await workflow_manager.register_workflow_template(workflow_template)
    
    # Create a workflow from the template
    parameter_values = {"url": "https://api.example.com/data"}
    workflow_id = await workflow_manager.create_workflow_from_template(
        template_id=template_id,
        parameter_values=parameter_values,
        workflow_name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        tags=["test", "example"],
    )
    
    # Verify workflow was created
    assert workflow_id is not None
    
    # Get the workflow from history
    workflow = await workflow_manager.workflow_history.get_workflow(workflow_id)
    
    # Verify workflow properties
    assert workflow.name == "Test Workflow"
    assert workflow.description == "A test workflow"
    assert workflow.created_by == "test_user"
    assert "test" in workflow.tags
    assert "example" in workflow.tags


@pytest.mark.asyncio
async def test_execute_workflow(workflow_manager, mock_agent, sample_workflow_steps):
    """Test executing a workflow."""
    # Register the agent
    await workflow_manager.register_agent(mock_agent)
    
    # Create a workflow
    workflow_id, version_id = await workflow_manager.workflow_history.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        steps=sample_workflow_steps,
    )
    
    # Configure mock agent to return success for both steps
    mock_agent.execute.side_effect = [
        {"status": "success", "result": "step1_result"},
        {"status": "success", "result": "step2_result"},
    ]
    
    # Execute the workflow
    result = await workflow_manager.execute_workflow(workflow_id)
    
    # Verify workflow execution result
    assert result["status"] == "success"
    assert len(result["completed_steps"]) == 2
    assert "step1" in result["completed_steps"]
    assert "step2" in result["completed_steps"]
    assert len(result["failed_steps"]) == 0
    
    # Verify agent was called for both steps
    assert mock_agent.execute.call_count == 2


@pytest.mark.asyncio
async def test_execute_workflow_with_failure(workflow_manager, mock_agent, sample_workflow_steps):
    """Test executing a workflow with a failing step."""
    # Register the agent
    await workflow_manager.register_agent(mock_agent)
    
    # Create a workflow
    workflow_id, version_id = await workflow_manager.workflow_history.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        steps=sample_workflow_steps,
    )
    
    # Configure mock agent to succeed for first step and fail for second step
    mock_agent.execute.side_effect = [
        {"status": "success", "result": "step1_result"},
        {"status": "failed", "error": "Step 2 failed"},
    ]
    
    # Execute the workflow
    result = await workflow_manager.execute_workflow(workflow_id)
    
    # Verify workflow execution result
    assert result["status"] == "partial_success"
    assert len(result["completed_steps"]) == 1
    assert "step1" in result["completed_steps"]
    assert len(result["failed_steps"]) == 1
    assert "step2" in result["failed_steps"]
    
    # Verify agent was called for both steps
    assert mock_agent.execute.call_count == 2


@pytest.mark.asyncio
async def test_execute_workflow_with_timeout(workflow_manager, mock_agent, sample_workflow_steps):
    """Test executing a workflow with a timeout."""
    # Register the agent
    await workflow_manager.register_agent(mock_agent)
    
    # Create a workflow
    workflow_id, version_id = await workflow_manager.workflow_history.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        steps=sample_workflow_steps,
    )
    
    # Configure mock agent to take longer than the timeout
    async def slow_execution(*args, **kwargs):
        import asyncio
        await asyncio.sleep(0.2)  # Simulate slow execution
        return {"status": "success", "result": "step1_result"}
    
    mock_agent.execute.side_effect = slow_execution
    
    # Execute the workflow with a very short timeout
    result = await workflow_manager.execute_workflow(workflow_id, execution_timeout=0.1)
    
    # Verify workflow execution result
    assert result["status"] == "timeout"
    assert "error" in result
    assert "timeout" in result["error"].lower()


@pytest.mark.asyncio
async def test_workflow_persistence(workflow_manager, workflow_template, tmp_path):
    """Test persisting and loading workflow state."""
    # Register a template
    template_id = await workflow_manager.register_workflow_template(workflow_template)
    
    # Create a workflow from the template
    parameter_values = {"url": "https://api.example.com/data"}
    workflow_id = await workflow_manager.create_workflow_from_template(
        template_id=template_id,
        parameter_values=parameter_values,
    )
    
    # Verify template was persisted
    templates_path = os.path.join(workflow_manager.persistence_path, "templates.json")
    assert os.path.exists(templates_path)
    
    # Create a new workflow manager with the same persistence path
    new_manager = WorkflowManager(persistence_path=workflow_manager.persistence_path)
    
    # Load persisted state
    await new_manager.load_persisted_state()
    
    # Verify templates were loaded
    assert template_id in new_manager.templates
    assert new_manager.templates[template_id].name == workflow_template.name
    
    # Verify workflow history was loaded
    workflow = await new_manager.workflow_history.get_workflow(workflow_id)
    assert workflow is not None
    assert workflow.name == workflow_template.name


@pytest.mark.asyncio
async def test_workflow_template_instantiation(workflow_template):
    """Test instantiating a workflow template with parameters."""
    # Instantiate the template
    parameter_values = {
        "url": "https://api.example.com/data",
        "format": "xml",
    }
    
    workflow_steps = workflow_template.instantiate(parameter_values)
    
    # Verify steps were created with substituted parameters
    assert len(workflow_steps) == 2
    assert workflow_steps[0].task.name == "fetch_data"
    assert workflow_steps[0].task.parameters["url"] == "https://api.example.com/data"
    assert workflow_steps[1].task.name == "process_data"
    assert workflow_steps[1].task.parameters["format"] == "xml"
    assert workflow_steps[1].dependencies == ["fetch_data"]


@pytest.mark.asyncio
async def test_workflow_template_with_missing_required_parameter(workflow_template):
    """Test instantiating a template with a missing required parameter."""
    # Try to instantiate with missing required parameter
    parameter_values = {
        "format": "xml",  # Missing required 'url' parameter
    }
    
    # Verify that an exception is raised
    with pytest.raises(ValueError) as excinfo:
        workflow_template.instantiate(parameter_values)
    
    # Verify the error message
    assert "Required parameter 'url' not provided" in str(excinfo.value)


@pytest.mark.asyncio
async def test_workflow_template_with_default_parameter(workflow_template):
    """Test instantiating a template with default parameter values."""
    # Instantiate with only required parameters (format should use default)
    parameter_values = {
        "url": "https://api.example.com/data",
    }
    
    workflow_steps = workflow_template.instantiate(parameter_values)
    
    # Verify default parameter was used
    assert workflow_steps[1].task.parameters["format"] == "json"