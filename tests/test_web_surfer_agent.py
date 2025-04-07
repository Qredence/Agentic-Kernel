"""Tests for the WebSurferAgent class."""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from pydantic import HttpUrl

from agentic_kernel.agents.web_surfer_agent import WebSurferAgent
from agentic_kernel.config_types import AgentConfig, LLMMapping
from agentic_kernel.types import Task


@pytest.fixture
def mock_web_surfer_plugin():
    """Create a mock WebSurferPlugin."""
    mock = MagicMock()
    mock.web_search.return_value = [
        MagicMock(
            model_dump=MagicMock(return_value={
                "title": "Test Result",
                "url": "https://example.com",
                "snippet": "This is a test result",
                "source": "Test"
            })
        )
    ]
    mock.summarize_webpage.return_value = "This is a test summary of a webpage."
    return mock


@pytest.fixture
def web_surfer_agent(mock_web_surfer_plugin):
    """Create a WebSurferAgent with a mock plugin."""
    with patch('agentic_kernel.agents.web_surfer_agent.WebSurferPlugin', 
               return_value=mock_web_surfer_plugin):
        agent_config = AgentConfig(
            name="web_surfer",
            type="WebSurferAgent",
            description="Web search agent for testing",
            llm_mapping=LLMMapping(
                model="gpt-4o-mini",
                endpoint="azure_openai"
            ),
            config={}
        )
        agent = WebSurferAgent(config=agent_config)
        return agent


@pytest.mark.asyncio
async def test_execute_search(web_surfer_agent):
    """Test searching for information."""
    task = Task(
        id="test-task-1",
        name="Web Search",
        description="search for test information",
        agent_type="web_surfer",
        parameters={},
        status="pending",
        max_retries=3
    )
    
    result = await web_surfer_agent.execute(task)
    
    assert result["status"] == "success"
    assert "search_results" in result["output"]
    assert len(result["output"]["search_results"]) == 1
    assert result["output"]["search_results"][0]["title"] == "Test Result"


@pytest.mark.asyncio
async def test_execute_summarize(web_surfer_agent):
    """Test summarizing a webpage."""
    task = Task(
        id="test-task-2",
        name="Web Summarize",
        description="summarize https://example.com",
        agent_type="web_surfer",
        parameters={},
        status="pending",
        max_retries=3
    )
    
    result = await web_surfer_agent.execute(task)
    
    assert result["status"] == "success"
    assert "summary" in result["output"]
    assert result["output"]["summary"] == "This is a test summary of a webpage."


@pytest.mark.asyncio
async def test_execute_summarize_with_url_in_context(web_surfer_agent):
    """Test summarizing a webpage with URL provided in context."""
    task = Task(
        id="test-task-3",
        name="Web Summarize",
        description="summarize this website",
        agent_type="web_surfer",
        parameters={"url": "https://example.com"},
        status="pending",
        max_retries=3
    )
    
    result = await web_surfer_agent.execute(task)
    
    assert result["status"] == "success"
    assert "summary" in result["output"]
    assert result["output"]["summary"] == "This is a test summary of a webpage."


@pytest.mark.asyncio
async def test_execute_with_invalid_url(web_surfer_agent):
    """Test behavior with invalid URL."""
    task = Task(
        id="test-task-4",
        name="Web Summarize",
        description="summarize htt://invalid-url",
        agent_type="web_surfer",
        parameters={},
        status="pending",
        max_retries=3
    )
    
    # URL parsing should fail, and agent should default to search
    result = await web_surfer_agent.execute(task)
    
    assert result["status"] == "success"
    assert "search_results" in result["output"] 