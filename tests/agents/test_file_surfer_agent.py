import pytest
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path
import datetime

# Assume FileSurferAgent will be in this location
from agentic_kernel.agents.file_surfer_agent import FileSurferAgent
from agentic_kernel.plugins.file_surfer import FileInfo # Needed for mocking return type

# Mock data
MOCK_BASE_PATH = Path("/mock/base").resolve()
MOCK_FILE_PATH_STR = "subdir/document.txt"
MOCK_FULL_FILE_PATH = MOCK_BASE_PATH / MOCK_FILE_PATH_STR
MOCK_FILE_CONTENT = "This is the content of the mock document."
MOCK_LIST_PATTERN = "*.txt"
MOCK_SEARCH_TEXT = "content"
MOCK_SEARCH_PATTERN = "*.txt"

MOCK_FILE_INFO_LIST = [
    FileInfo(
        name="document.txt",
        path=MOCK_FULL_FILE_PATH,
        size=100,
        content_type="text/plain",
        last_modified=datetime.datetime.now().isoformat()
    ),
    FileInfo(
        name="another.txt",
        path=MOCK_BASE_PATH / "another.txt",
        size=50,
        content_type="text/plain",
        last_modified=datetime.datetime.now().isoformat()
    )
]

@pytest.fixture
def mock_plugin():
    """Fixture to create a mock FileSurferPlugin."""
    plugin = MagicMock()
    plugin.base_path = MOCK_BASE_PATH # Set the base path on the mock
    plugin.list_files.return_value = MOCK_FILE_INFO_LIST
    plugin.read_file.return_value = MOCK_FILE_CONTENT
    plugin.search_files.return_value = [MOCK_FILE_INFO_LIST[0]] # Assume only first file matches search
    return plugin

# Use this patch target based on where FileSurferPlugin is imported in the agent file
PLUGIN_PATCH_TARGET = 'agentic_kernel.agents.file_surfer_agent.FileSurferPlugin'

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_file_surfer_agent_initialization(MockFileSurferPlugin, mock_plugin):
    """Test agent initialization."""
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    assert agent.name == "FileSurfer"
    assert agent.plugin is not None
    MockFileSurferPlugin.assert_called_once_with(base_path=MOCK_BASE_PATH)

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_execute_list_task(MockFileSurferPlugin, mock_plugin):
    """Test executing a list files task."""
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    task_desc = f"list files matching {MOCK_LIST_PATTERN}"

    result = await agent.execute_task(task_description=task_desc)

    assert result['status'] == 'success'
    assert 'files_listed' in result['output']
    # Check if the output matches the Pydantic model dump of the mock data
    expected_output = [r.model_dump(mode='json') for r in MOCK_FILE_INFO_LIST]
    assert result['output']['files_listed'] == expected_output
    mock_plugin.list_files.assert_called_once_with(pattern=MOCK_LIST_PATTERN, recursive=False)
    mock_plugin.read_file.assert_not_called()
    mock_plugin.search_files.assert_not_called()

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_execute_list_task_recursive(MockFileSurferPlugin, mock_plugin):
    """Test recursive list files task."""
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    task_desc = f"list *.py files recursively"

    await agent.execute_task(task_description=task_desc)

    mock_plugin.list_files.assert_called_once_with(pattern="*.py", recursive=True)

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_execute_read_task(MockFileSurferPlugin, mock_plugin):
    """Test executing a read file task."""
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    task_desc = f"read the file {MOCK_FILE_PATH_STR}"

    result = await agent.execute_task(task_description=task_desc)

    assert result['status'] == 'success'
    assert result['output'] == {'file_content': MOCK_FILE_CONTENT}
    mock_plugin.read_file.assert_called_once_with(file_path=MOCK_FILE_PATH_STR)
    mock_plugin.list_files.assert_not_called()
    mock_plugin.search_files.assert_not_called()

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_execute_search_task(MockFileSurferPlugin, mock_plugin):
    """Test executing a search files task."""
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    task_desc = f"search for '{MOCK_SEARCH_TEXT}' in files matching {MOCK_SEARCH_PATTERN}"

    result = await agent.execute_task(task_description=task_desc)

    assert result['status'] == 'success'
    assert 'files_found' in result['output']
    expected_output = [MOCK_FILE_INFO_LIST[0].model_dump(mode='json')] # Only the first file matched
    assert result['output']['files_found'] == expected_output
    mock_plugin.search_files.assert_called_once_with(text=MOCK_SEARCH_TEXT, file_pattern=MOCK_SEARCH_PATTERN)
    mock_plugin.list_files.assert_not_called()
    mock_plugin.read_file.assert_not_called()

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_execute_unknown_action(MockFileSurferPlugin, mock_plugin):
    """Test task description that doesn't match known actions."""
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    task_desc = "what is the modification time of file.txt?"

    result = await agent.execute_task(task_description=task_desc)

    assert result['status'] == 'failure'
    assert 'Could not determine file action' in result['error_message']
    mock_plugin.list_files.assert_not_called()
    mock_plugin.read_file.assert_not_called()
    mock_plugin.search_files.assert_not_called()

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_read_file_not_specified(MockFileSurferPlugin, mock_plugin):
    """Test read action when file path is missing."""
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    task_desc = "read content"

    result = await agent.execute_task(task_description=task_desc)

    assert result['status'] == 'failure'
    assert 'File path not specified' in result['error_message']

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_search_text_not_specified(MockFileSurferPlugin, mock_plugin):
    """Test search action when search text is missing or badly quoted."""
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    task_desc = "search for unquoted text in *.txt"

    result = await agent.execute_task(task_description=task_desc)

    assert result['status'] == 'failure'
    assert 'Search text not specified' in result['error_message']

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_handle_list_error(MockFileSurferPlugin, mock_plugin):
    """Test handling exceptions during list_files."""
    mock_plugin.list_files.side_effect = Exception("Permission denied")
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    task_desc = "list *.log files"

    result = await agent.execute_task(task_description=task_desc)

    assert result['status'] == 'failure'
    assert 'An unexpected error occurred during list' in result['error_message']
    assert 'Permission denied' in result['error_message']

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_handle_read_error(MockFileSurferPlugin, mock_plugin):
    """Test handling exceptions during read_file."""
    mock_plugin.read_file.side_effect = FileNotFoundError("No such file")
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    task_desc = "read missing_file.txt"

    result = await agent.execute_task(task_description=task_desc)

    assert result['status'] == 'failure'
    assert 'An unexpected error occurred during read' in result['error_message']
    assert 'No such file' in result['error_message'] # Check original exception is included

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_handle_plugin_read_error_string(MockFileSurferPlugin, mock_plugin):
    """Test handling specific error string returned by plugin's read_file."""
    error_string = "Error reading file: Access denied: File is outside base directory"
    mock_plugin.read_file.return_value = error_string
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    task_desc = "read ../../etc/passwd" # Example of trying to read outside base path

    result = await agent.execute_task(task_description=task_desc)

    assert result['status'] == 'failure'
    assert result['error_message'] == error_string

@pytest.mark.asyncio
@patch(PLUGIN_PATCH_TARGET)
async def test_handle_search_error(MockFileSurferPlugin, mock_plugin):
    """Test handling exceptions during search_files."""
    mock_plugin.search_files.side_effect = Exception("Disk error")
    MockFileSurferPlugin.return_value = mock_plugin
    agent = FileSurferAgent(config={'plugin_config': {'base_path': str(MOCK_BASE_PATH)}})
    task_desc = "search for 'important' in *.doc"

    result = await agent.execute_task(task_description=task_desc)

    assert result['status'] == 'failure'
    assert 'An unexpected error occurred during search' in result['error_message']
    assert 'Disk error' in result['error_message'] 