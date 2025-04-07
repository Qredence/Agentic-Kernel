"""Tests for the CoderAgent class."""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from agentic_kernel.agents.coder_agent import CoderAgent
from agentic_kernel.config_types import AgentConfig, LLMMapping
from agentic_kernel.types import Task


@pytest.fixture
def mock_llm():
    """Create a mock LLM for the CoderAgent."""
    mock = MagicMock()
    
    # Set up return values for different methods
    mock.generate_code.return_value = {
        "code": "def hello_world():\n    print('Hello, World!')",
        "language": "python",
        "explanation": "A simple hello world function."
    }
    
    mock.review_code.return_value = {
        "issues": ["Missing docstring"],
        "suggestions": ["Add a docstring to explain the function's purpose"],
        "quality_score": 8.5
    }
    
    mock.refactor_code.return_value = {
        "refactored_code": "def hello_world():\n    \"\"\"Print a greeting.\"\"\"\n    print('Hello, World!')",
        "changes": ["Added docstring"],
        "improvement_metrics": {"readability": "+20%"}
    }
    
    mock.explain_code.return_value = {
        "explanation": "This function prints 'Hello, World!' to the console.",
        "complexity_analysis": "O(1) - constant time",
        "key_concepts": ["functions", "print statements"]
    }
    
    return mock


@pytest.fixture
def coder_agent(mock_llm):
    """Create a CoderAgent with a mock LLM."""
    agent_config = AgentConfig(
        name="coder",
        type="CoderAgent",
        description="Code generation and review agent for testing",
        llm_mapping=LLMMapping(
            model="gpt-4o-mini",
            endpoint="azure_openai",
            max_tokens=2000,
            temperature=0.7
        ),
        config={"supported_languages": ["python", "javascript"]}
    )
    agent = CoderAgent(config=agent_config, llm=mock_llm)
    return agent


@pytest.mark.asyncio
async def test_execute_generate_code(coder_agent, mock_llm):
    """Test code generation."""
    task = Task(
        id="test-task-1",
        name="Generate Code",
        description="Create a hello world function",
        agent_type="coder",
        parameters={"action": "generate", "language": "python"},
        status="pending",
        max_retries=3
    )
    
    result = await coder_agent.execute(task)
    
    assert result["status"] == "success"
    assert "output" in result
    mock_llm.generate_code.assert_called_once_with(
        "Create a hello world function",
        language="python",
        max_tokens=2000,
        temperature=0.7
    )


@pytest.mark.asyncio
async def test_execute_review_code(coder_agent, mock_llm):
    """Test code review."""
    task = Task(
        id="test-task-2",
        name="Review Code",
        description="Review this Python code",
        agent_type="coder",
        parameters={
            "action": "review", 
            "language": "python",
            "code": "def hello_world():\n    print('Hello, World!')"
        },
        status="pending",
        max_retries=3
    )
    
    result = await coder_agent.execute(task)
    
    assert result["status"] == "success"
    assert "output" in result
    mock_llm.review_code.assert_called_once_with(
        "def hello_world():\n    print('Hello, World!')", 
        "python"
    )


@pytest.mark.asyncio
async def test_execute_refactor_code(coder_agent, mock_llm):
    """Test code refactoring."""
    task = Task(
        id="test-task-3",
        name="Refactor Code",
        description="Refactor this Python code for better readability",
        agent_type="coder",
        parameters={
            "action": "refactor", 
            "language": "python",
            "code": "def hello_world():\n    print('Hello, World!')",
            "goals": ["improve_readability"]
        },
        status="pending",
        max_retries=3
    )
    
    result = await coder_agent.execute(task)
    
    assert result["status"] == "success"
    assert "output" in result
    mock_llm.refactor_code.assert_called_once_with(
        "def hello_world():\n    print('Hello, World!')",
        language="python",
        goals=["improve_readability"],
        max_tokens=2000,
        temperature=0.7
    )


@pytest.mark.asyncio
async def test_execute_explain_code(coder_agent, mock_llm):
    """Test code explanation."""
    task = Task(
        id="test-task-4",
        name="Explain Code",
        description="Explain this Python code",
        agent_type="coder",
        parameters={
            "action": "explain", 
            "language": "python",
            "code": "def hello_world():\n    print('Hello, World!')"
        },
        status="pending",
        max_retries=3
    )
    
    result = await coder_agent.execute(task)
    
    assert result["status"] == "success"
    assert "output" in result
    mock_llm.explain_code.assert_called_once_with(
        "def hello_world():\n    print('Hello, World!')", 
        "python"
    )


@pytest.mark.asyncio
async def test_execute_unsupported_action(coder_agent):
    """Test behavior with unsupported action."""
    task = Task(
        id="test-task-5",
        name="Unknown Action",
        description="Do something with code",
        agent_type="coder",
        parameters={
            "action": "optimize", 
            "language": "python",
            "code": "def hello_world():\n    print('Hello, World!')"
        },
        status="pending",
        max_retries=3
    )
    
    result = await coder_agent.execute(task)
    
    assert result["status"] == "error"
    assert "error" in result
    assert "Unsupported action: optimize" in result["error"]


@pytest.mark.asyncio
async def test_execute_unsupported_language(coder_agent):
    """Test behavior with unsupported programming language."""
    task = Task(
        id="test-task-6",
        name="Generate Code",
        description="Create a hello world function in Rust",
        agent_type="coder",
        parameters={"action": "generate", "language": "rust"},
        status="pending",
        max_retries=3
    )
    
    result = await coder_agent.execute(task)
    
    assert result["status"] == "error"
    assert "error" in result
    assert "Unsupported language: rust" in result["error"]


def test_supports_language(coder_agent):
    """Test language support checking."""
    assert coder_agent.supports_language("python") is True
    assert coder_agent.supports_language("javascript") is True
    assert coder_agent.supports_language("rust") is False


def test_add_supported_language(coder_agent):
    """Test adding a supported language."""
    assert coder_agent.supports_language("rust") is False
    
    coder_agent.add_supported_language("rust")
    
    assert coder_agent.supports_language("rust") is True
    assert "rust" in coder_agent.supported_languages


def test_remove_supported_language(coder_agent):
    """Test removing a supported language."""
    assert coder_agent.supports_language("javascript") is True
    
    coder_agent.remove_supported_language("javascript")
    
    assert coder_agent.supports_language("javascript") is False
    assert "javascript" not in coder_agent.supported_languages
    
    # Python should not be removable
    coder_agent.remove_supported_language("python")
    assert coder_agent.supports_language("python") is True 