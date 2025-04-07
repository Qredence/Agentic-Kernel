"""Tests for the FileSurferAgent class."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from agentic_kernel.agents.file_surfer_agent import FileSurferAgent
from agentic_kernel.config_types import AgentConfig, LLMMapping
from agentic_kernel.types import Task


@pytest.fixture
def mock_file_info():
    """Create a mock FileInfo object."""
    mock = MagicMock()
    mock.model_dump.return_value = {
        "name": "test.txt",
        "path": "/path/to/test.txt",
        "size": 100,
        "content_type": "text/plain",
        "last_modified": "2025-04-06T12:00:00"
    }
    return mock


@pytest.fixture
def mock_file_surfer_plugin(mock_file_info):
    """Create a mock FileSurferPlugin."""
    mock = MagicMock()
    mock.list_files.return_value = [mock_file_info]
    mock.read_file.return_value = "This is the content of test.txt"
    mock.search_files.return_value = [mock_file_info]
    return mock


@pytest.fixture
def file_surfer_agent(mock_file_surfer_plugin):
    """Create a FileSurferAgent with a mock plugin."""
    with patch('agentic_kernel.agents.file_surfer_agent.FileSurferPlugin', 
               return_value=mock_file_surfer_plugin):
        agent_config = AgentConfig(
            name="file_surfer",
            type="FileSurferAgent",
            description="File operations agent for testing",
            llm_mapping=LLMMapping(
                model="gpt-4o-mini",
                endpoint="azure_openai"
            ),
            config={}
        )
        agent = FileSurferAgent(config=agent_config)
        return agent


@pytest.mark.asyncio
async def test_execute_list_files(file_surfer_agent):
    """Test listing files."""
    task = Task(
        id="test-task-1",
        name="List Files",
        description="list *.py files",
        agent_type="file_surfer",
        parameters={},
        status="pending",
        max_retries=3
    )
    
    result = await file_surfer_agent.execute(task)
    
    assert result["status"] == "success"
    assert "files_listed" in result["output"]
    assert len(result["output"]["files_listed"]) == 1
    assert result["output"]["files_listed"][0]["name"] == "test.txt"


@pytest.mark.asyncio
async def test_execute_read_file(file_surfer_agent):
    """Test reading a file."""
    task = Task(
        id="test-task-2",
        name="Read File",
        description="read test.txt",
        agent_type="file_surfer",
        parameters={},
        status="pending",
        max_retries=3
    )
    
    result = await file_surfer_agent.execute(task)
    
    assert result["status"] == "success"
    assert "file_content" in result["output"]
    assert result["output"]["file_content"] == "This is the content of test.txt"


@pytest.mark.asyncio
async def test_execute_search_files(file_surfer_agent):
    """Test searching for files containing specific text."""
    task = Task(
        id="test-task-3",
        name="Search Files",
        description="search for 'test' in *.py",
        agent_type="file_surfer",
        parameters={},
        status="pending",
        max_retries=3
    )
    
    result = await file_surfer_agent.execute(task)
    
    assert result["status"] == "success"
    assert "files_found" in result["output"]
    assert len(result["output"]["files_found"]) == 1
    assert result["output"]["files_found"][0]["name"] == "test.txt"


@pytest.mark.asyncio
async def test_execute_unknown_action(file_surfer_agent):
    """Test behavior with unknown action."""
    task = Task(
        id="test-task-4",
        name="Unknown Action",
        description="do something with files",
        agent_type="file_surfer",
        parameters={},
        status="pending",
        max_retries=3
    )
    
    result = await file_surfer_agent.execute(task)
    
    assert result["status"] == "failure"
    assert "error_message" in result
    assert "Could not determine file action" in result["error_message"] 