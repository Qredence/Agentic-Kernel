"""Tests for the agent selection functionality."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from src.agentic_kernel.orchestrator.agent_selection import AgentSelector, AgentSkillMatrix
from src.agentic_kernel.types import Task
from src.agentic_kernel.agents.base import BaseAgent
from src.agentic_kernel.config import AgentConfig


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    def __init__(self, agent_type, capabilities=None):
        config = AgentConfig(name=f"{agent_type}_agent", model="mock_model")
        super().__init__(config)
        self.type = agent_type
        self._capabilities = capabilities or {}
        
    async def execute(self, task):
        """Mock execute method."""
        return {"status": "success", "output": {"result": "mock_result"}}
        
    def _get_supported_tasks(self):
        """Return mock capabilities."""
        return self._capabilities
        
    async def reset(self):
        """Mock reset method."""
        pass


@pytest.fixture
def skill_matrix():
    """Create a test AgentSkillMatrix."""
    return AgentSkillMatrix()


@pytest.fixture
def agent_selector():
    """Create a test AgentSelector."""
    return AgentSelector()


@pytest.fixture
def mock_agents():
    """Create a dictionary of mock agents for testing."""
    web_agent = MockAgent("web", {
        "search_web": {
            "description": "Search the web for information",
            "parameters": ["query", "num_results"]
        },
        "navigate_url": {
            "description": "Navigate to a specific URL",
            "parameters": ["url"]
        }
    })
    
    code_agent = MockAgent("code", {
        "write_code": {
            "description": "Write code in a specific language",
            "parameters": ["language", "requirements"]
        },
        "debug_code": {
            "description": "Debug existing code",
            "parameters": ["code", "error_message"]
        }
    })
    
    data_agent = MockAgent("data", {
        "analyze_data": {
            "description": "Analyze structured data",
            "parameters": ["data", "analysis_type"]
        },
        "visualize_data": {
            "description": "Create visualizations from data",
            "parameters": ["data", "chart_type"]
        }
    })
    
    return {
        web_agent.agent_id: web_agent,
        code_agent.agent_id: code_agent,
        data_agent.agent_id: data_agent
    }


async def register_mock_agents(skill_matrix, agents):
    """Register mock agents with the skill matrix."""
    for agent in agents.values():
        await skill_matrix.register_agent_capabilities(agent)


@pytest.mark.asyncio
async def test_agent_selection_by_type(agent_selector, mock_agents):
    """Test selecting an agent based on type."""
    # Create a task that specifies agent type
    task = Task(
        name="search_for_info",
        description="Search the web for information about Python",
        agent_type="web",
        parameters={"query": "Python programming"}
    )
    
    # Register agents with the selector
    for agent in mock_agents.values():
        await agent_selector.skill_matrix.register_agent_capabilities(agent)
    
    # Select an agent for the task
    selected_id = await agent_selector.select_agent(task, mock_agents)
    selected_agent = mock_agents[selected_id]
    
    # Verify correct agent type selected
    assert selected_agent.type == "web"


@pytest.mark.asyncio
async def test_agent_selection_by_capability(agent_selector, mock_agents):
    """Test selecting an agent based on capabilities."""
    # Create a task that doesn't specify agent type
    task = Task(
        name="write_python_code",
        description="Write Python code to solve a problem",
        agent_type="any",
        parameters={"language": "python", "requirements": "Create a simple web server"}
    )
    
    # Register agents with the selector
    for agent in mock_agents.values():
        await agent_selector.skill_matrix.register_agent_capabilities(agent)
    
    # Select an agent for the task
    selected_id = await agent_selector.select_agent(task, mock_agents)
    selected_agent = mock_agents[selected_id]
    
    # Verify correct agent type selected based on capability match
    assert selected_agent.type == "code"


@pytest.mark.asyncio
async def test_agent_selection_with_specialization(agent_selector, mock_agents):
    """Test selecting an agent with domain specialization."""
    # Register agents with the selector
    for agent in mock_agents.values():
        await agent_selector.skill_matrix.register_agent_capabilities(agent)
    
    # Register specialization for one agent
    code_agent_id = next(agent_id for agent_id, agent in mock_agents.items() 
                         if agent.type == "code")
    agent_selector.skill_matrix.register_agent_specialization(
        code_agent_id, ["machine_learning", "web_development"]
    )
    
    # Create a task that matches the specialization
    task = Task(
        name="create_ml_model",
        description="Create a machine learning model for classification",
        agent_type="any",
        parameters={"model_type": "classification", "data_source": "csv_file"}
    )
    
    # Select an agent for the task
    selected_id = await agent_selector.select_agent(task, mock_agents)
    selected_agent = mock_agents[selected_id]
    
    # Verify specialized agent was selected
    assert selected_agent.type == "code"


@pytest.mark.asyncio
async def test_agent_selection_with_performance_history(agent_selector, mock_agents):
    """Test selecting an agent based on performance history."""
    # Register agents with the selector
    for agent in mock_agents.values():
        await agent_selector.skill_matrix.register_agent_capabilities(agent)
    
    # Create multiple agents of the same type
    web_agent1 = MockAgent("web", {
        "search_web": {
            "description": "Search the web for information",
            "parameters": ["query"]
        }
    })
    web_agent2 = MockAgent("web", {
        "search_web": {
            "description": "Search the web for information",
            "parameters": ["query"]
        }
    })
    
    mock_agents[web_agent1.agent_id] = web_agent1
    mock_agents[web_agent2.agent_id] = web_agent2
    
    await agent_selector.skill_matrix.register_agent_capabilities(web_agent1)
    await agent_selector.skill_matrix.register_agent_capabilities(web_agent2)
    
    # Add performance history - make web_agent2 perform better
    agent_selector.skill_matrix.update_agent_performance(web_agent1.agent_id, True, 2.0)
    agent_selector.skill_matrix.update_agent_performance(web_agent2.agent_id, True, 1.0)
    agent_selector.skill_matrix.update_agent_performance(web_agent2.agent_id, True, 0.8)
    
    # Create a task specifying the web agent type
    task = Task(
        name="search_info",
        description="Search for weather information",
        agent_type="web",
        parameters={"query": "weather forecast"}
    )
    
    # Select an agent for the task
    selected_id = await agent_selector.select_agent(task, mock_agents)
    
    # Verify the better performing agent was selected
    assert selected_id == web_agent2.agent_id


@pytest.mark.asyncio
async def test_agent_selection_fallback(agent_selector, mock_agents):
    """Test fallback selection when no perfect match is found."""
    # Create a task with no matching capabilities
    task = Task(
        name="unknown_task",
        description="Task with no direct capability match",
        agent_type="unknown",
        parameters={"param1": "value1"}
    )
    
    # Register agents with the selector
    for agent in mock_agents.values():
        await agent_selector.skill_matrix.register_agent_capabilities(agent)
    
    # Add a generalist agent
    generalist = MockAgent("generalist", {
        "handle_any_task": {
            "description": "Handle any type of task",
            "parameters": ["task_details"]
        }
    })
    mock_agents[generalist.agent_id] = generalist
    await agent_selector.skill_matrix.register_agent_capabilities(generalist)
    
    # Select an agent for the task
    selected_id = await agent_selector.select_agent(task, mock_agents)
    selected_agent = mock_agents[selected_id]
    
    # Verify fallback to generalist agent
    assert selected_agent.type == "generalist"


@pytest.mark.asyncio
async def test_orchestrator_agent_selection_integration():
    """Test integration with OrchestratorAgent."""
    from src.agentic_kernel.orchestrator.core import OrchestratorAgent
    from src.agentic_kernel.ledgers import TaskLedger, ProgressLedger
    
    # Create mock ledgers
    task_ledger = MagicMock(spec=TaskLedger)
    progress_ledger = MagicMock(spec=ProgressLedger)
    
    # Create orchestrator
    config = AgentConfig(name="test_orchestrator", model="test_model")
    orchestrator = OrchestratorAgent(config, task_ledger, progress_ledger)
    
    # Create and register mock agents
    web_agent = MockAgent("web")
    code_agent = MockAgent("code")
    data_agent = MockAgent("data")
    
    orchestrator.register_agent(web_agent)
    orchestrator.register_agent(code_agent)
    orchestrator.register_agent(data_agent)
    
    # Register specializations
    orchestrator.register_agent_specialization(web_agent.agent_id, ["search", "browsing"])
    orchestrator.register_agent_specialization(code_agent.agent_id, ["development", "programming"])
    
    # Create a task
    task = Task(
        name="write_code",
        description="Write a Python function to calculate fibonacci numbers",
        agent_type="any",
        parameters={"language": "python"}
    )
    
    # Select agent for task
    selected_agent = await orchestrator.select_agent_for_task(task)
    
    # Verify agent selection works
    assert selected_agent is not None
    assert selected_agent.type == "code"
    
    # Test with a task that specifies agent type
    task_with_type = Task(
        name="search_info",
        description="Search for information about Python",
        agent_type="web",
        parameters={"query": "Python programming"}
    )
    
    selected_agent = await orchestrator.select_agent_for_task(task_with_type)
    assert selected_agent is not None
    assert selected_agent.type == "web" 