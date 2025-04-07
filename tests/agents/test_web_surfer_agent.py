import pytest
import asyncio
from unittest.mock import patch, MagicMock

from pydantic import HttpUrl

# Assume WebSurferAgent will be in this location
from agentic_kernel.agents.web_surfer_agent import WebSurferAgent
from agentic_kernel.plugins.web_surfer import WebSearchResult # Needed for mocking return type

# Mock data
MOCK_SEARCH_QUERY = "large language models"
MOCK_SEARCH_RESULTS = [
    WebSearchResult(title="LLM Title 1", url="https://example.com/llm1", snippet="Snippet 1", source="TestSource"),
    WebSearchResult(title="LLM Title 2", url="https://example.com/llm2", snippet="Snippet 2", source="TestSource")
]
MOCK_URL_TO_SUMMARIZE = HttpUrl("https://example.com/article")
MOCK_SUMMARY = "This is a summary of the article content."
MOCK_INVALID_URL_STRING = "htp:/invalid-url"

@pytest.fixture
def mock_plugin():
    """Fixture to create a mock WebSurferPlugin."""
    plugin = MagicMock()
    plugin.web_search.return_value = MOCK_SEARCH_RESULTS
    plugin.summarize_webpage.return_value = MOCK_SUMMARY
    return plugin

@pytest.mark.asyncio
@patch('agentic_kernel.agents.web_surfer_agent.WebSurferPlugin') # Patch the plugin import within the agent file
async def test_web_surfer_agent_initialization(MockWebSurferPlugin, mock_plugin):
    """Test that the agent initializes correctly and instantiates the plugin."""
    MockWebSurferPlugin.return_value = mock_plugin
    agent = WebSurferAgent()
    assert agent.name == "WebSurfer"
    assert agent.plugin is not None
    MockWebSurferPlugin.assert_called_once() # Check plugin was instantiated

@pytest.mark.asyncio
@patch('agentic_kernel.agents.web_surfer_agent.WebSurferPlugin')
async def test_execute_search_task(MockWebSurferPlugin, mock_plugin):
    """Test executing a search task."""
    MockWebSurferPlugin.return_value = mock_plugin
    agent = WebSurferAgent()
    
    result = await agent.execute_task(task_description=MOCK_SEARCH_QUERY)
    
    assert result['status'] == 'success'
    assert 'search_results' in result['output']
    assert len(result['output']['search_results']) == len(MOCK_SEARCH_RESULTS)
    # Use model_dump() for comparison if Pydantic v2
    assert result['output']['search_results'] == [r.model_dump() for r in MOCK_SEARCH_RESULTS]
    mock_plugin.web_search.assert_called_once_with(query=MOCK_SEARCH_QUERY)
    mock_plugin.summarize_webpage.assert_not_called()

@pytest.mark.asyncio
@patch('agentic_kernel.agents.web_surfer_agent.WebSurferPlugin')
async def test_execute_summarize_task_url_in_description(MockWebSurferPlugin, mock_plugin):
    """Test executing a summarization task with URL in description."""
    MockWebSurferPlugin.return_value = mock_plugin
    agent = WebSurferAgent()
    task_desc = f"Please summarize the article at {MOCK_URL_TO_SUMMARIZE}"
    
    result = await agent.execute_task(task_description=task_desc)
    
    assert result['status'] == 'success'
    assert result['output'] == {'summary': MOCK_SUMMARY}
    mock_plugin.summarize_webpage.assert_called_once_with(url=MOCK_URL_TO_SUMMARIZE)
    mock_plugin.web_search.assert_not_called()

@pytest.mark.asyncio
@patch('agentic_kernel.agents.web_surfer_agent.WebSurferPlugin')
async def test_execute_summarize_task_url_in_context(MockWebSurferPlugin, mock_plugin):
    """Test executing a summarization task with URL in context."""
    MockWebSurferPlugin.return_value = mock_plugin
    agent = WebSurferAgent()
    context = {'url': str(MOCK_URL_TO_SUMMARIZE)} # Context needs string URL
    task_desc = "Summarize the provided URL."
    
    result = await agent.execute_task(task_description=task_desc, context=context)
    
    assert result['status'] == 'success'
    assert result['output'] == {'summary': MOCK_SUMMARY}
    mock_plugin.summarize_webpage.assert_called_once_with(url=MOCK_URL_TO_SUMMARIZE)
    mock_plugin.web_search.assert_not_called()

@pytest.mark.asyncio
@patch('agentic_kernel.agents.web_surfer_agent.WebSurferPlugin')
async def test_execute_invalid_url_in_description(MockWebSurferPlugin, mock_plugin):
    """Test handling of an invalid URL in the description."""
    MockWebSurferPlugin.return_value = mock_plugin
    agent = WebSurferAgent()
    task_desc = f"Summarize this: {MOCK_INVALID_URL_STRING}"
    
    result = await agent.execute_task(task_description=task_desc)
    
    assert result['status'] == 'failure'
    assert 'Invalid URL format' in result['error_message']
    assert MOCK_INVALID_URL_STRING in result['error_message']
    mock_plugin.summarize_webpage.assert_not_called()
    mock_plugin.web_search.assert_not_called()

@pytest.mark.asyncio
@patch('agentic_kernel.agents.web_surfer_agent.WebSurferPlugin')
async def test_handle_search_error(MockWebSurferPlugin, mock_plugin):
    """Test handling exceptions during web search."""
    mock_plugin.web_search.side_effect = Exception("Search API down")
    MockWebSurferPlugin.return_value = mock_plugin
    agent = WebSurferAgent()
    
    result = await agent.execute_task(task_description=MOCK_SEARCH_QUERY)
    
    assert result['status'] == 'failure'
    assert 'An unexpected error occurred during web search' in result['error_message']
    assert 'Search API down' in result['error_message']
    mock_plugin.web_search.assert_called_once_with(query=MOCK_SEARCH_QUERY)
    mock_plugin.summarize_webpage.assert_not_called()

@pytest.mark.asyncio
@patch('agentic_kernel.agents.web_surfer_agent.WebSurferPlugin')
async def test_handle_summarization_error(MockWebSurferPlugin, mock_plugin):
    """Test handling exceptions during summarization."""
    mock_plugin.summarize_webpage.side_effect = Exception("Network error")
    MockWebSurferPlugin.return_value = mock_plugin
    agent = WebSurferAgent()
    task_desc = f"Summarize {MOCK_URL_TO_SUMMARIZE}"
    
    result = await agent.execute_task(task_description=task_desc)
    
    assert result['status'] == 'failure'
    assert 'An unexpected error occurred during summarization' in result['error_message']
    assert 'Network error' in result['error_message']
    mock_plugin.summarize_webpage.assert_called_once_with(url=MOCK_URL_TO_SUMMARIZE)
    mock_plugin.web_search.assert_not_called()

@pytest.mark.asyncio
@patch('agentic_kernel.agents.web_surfer_agent.WebSurferPlugin')
async def test_handle_plugin_summarization_error_string(MockWebSurferPlugin, mock_plugin):
    """Test handling error string returned by the plugin's summarize function."""
    error_string = "Error summarizing webpage: Timeout"
    mock_plugin.summarize_webpage.return_value = error_string
    MockWebSurferPlugin.return_value = mock_plugin
    agent = WebSurferAgent()
    task_desc = f"Summarize {MOCK_URL_TO_SUMMARIZE}"

    result = await agent.execute_task(task_description=task_desc)

    assert result['status'] == 'failure'
    assert result['error_message'] == error_string
    mock_plugin.summarize_webpage.assert_called_once_with(url=MOCK_URL_TO_SUMMARIZE)
    mock_plugin.web_search.assert_not_called() 