"""Tests for MCP (Model Control Protocol) functionality."""

import pytest
import chainlit as cl
from mcp import ClientSession
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_mcp_session():
    """Create a mock MCP session."""
    session = AsyncMock(spec=ClientSession)
    tool = MagicMock()
    tool.name = "test_tool"  # Set name as a string attribute
    tool.description = "A test tool"
    tool.inputSchema = {"type": "object", "properties": {}}
    
    session.list_tools = AsyncMock(return_value=MagicMock(
        tools=[tool]
    ))
    session.call_tool = AsyncMock(return_value="Tool execution result")
    return session

@pytest.fixture
def mock_connection():
    """Create a mock MCP connection."""
    connection = MagicMock()
    connection.name = "test_connection"
    return connection

@pytest.mark.asyncio
async def test_mcp_connect(mock_mcp_session, mock_connection):
    """Test MCP connection handler."""
    with patch.object(cl, 'user_session') as mock_user_session:
        mock_user_session.get.return_value = {}
        
        from app import on_mcp_connect
        await on_mcp_connect(mock_connection, mock_mcp_session)
        
        # Verify tools were stored
        mock_user_session.get.assert_called_with("mcp_tools", {})
        mock_user_session.set.assert_called_once()
        
        # Verify tool metadata was processed correctly
        tools_dict = mock_user_session.set.call_args[0][1]
        assert "test_connection" in tools_dict
        assert len(tools_dict["test_connection"]) == 1
        assert tools_dict["test_connection"][0]["name"] == "test_tool"

@pytest.mark.asyncio
async def test_mcp_disconnect(mock_mcp_session):
    """Test MCP disconnection handler."""
    with patch.object(cl, 'user_session') as mock_user_session:
        mock_user_session.get.return_value = {
            "test_connection": [{"name": "test_tool"}]
        }
        
        from app import on_mcp_disconnect
        await on_mcp_disconnect("test_connection", mock_mcp_session)
        
        # Verify tools were cleaned up
        mock_user_session.get.assert_called_with("mcp_tools", {})
        mock_user_session.set.assert_called_once()
        
        # Verify tool was removed
        tools_dict = mock_user_session.set.call_args[0][1]
        assert "test_connection" not in tools_dict

class AsyncIteratorMock:
    """Mock async iterator for testing."""
    def __init__(self, items):
        self.items = items
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)

@pytest.mark.asyncio
async def test_chat_agent_with_mcp_tools(mock_mcp_session, mock_connection):
    """Test ChatAgent handling of MCP tools."""
    from app import ChatAgent, AgentConfig
    import semantic_kernel as sk
    
    # Setup mock kernel
    kernel = MagicMock(spec=sk.Kernel)
    service = AsyncMock()
    mock_chunk = MagicMock()
    mock_function = MagicMock()
    mock_function.name = "test_tool"  # Set name as a string attribute
    mock_function.arguments = {"arg": "value"}
    mock_chunk.tool_calls = [MagicMock(function=mock_function)]
    mock_chunk.__str__ = lambda self: "Response text"
    
    # Create async iterator for stream
    async def get_stream(*args, **kwargs):
        return AsyncIteratorMock([mock_chunk])
    
    service.get_streaming_chat_message_content = get_stream
    kernel.get_service.return_value = service
    
    # Setup mock config loader
    config_loader = MagicMock()
    config_loader.get_model_config.return_value = {}
    
    # Create chat agent
    agent = ChatAgent(
        config=AgentConfig(name="test", model="test-model", endpoint="test-endpoint"),
        kernel=kernel,
        config_loader=config_loader
    )
    
    # Setup mock user session
    with patch.object(cl, 'user_session') as mock_user_session:
        mock_user_session.get.return_value = {
            "test_connection": [{
                "name": "test_tool",
                "description": "A test tool",
                "input_schema": {"type": "object", "properties": {}}
            }]
        }
        mock_user_session.mcp_sessions = {
            "test_connection": (mock_mcp_session, None)
        }
        
        # Test message handling
        response = []
        async for chunk in agent.handle_message("Test message"):
            response.append(chunk)
        
        # Verify tool was called
        mock_mcp_session.call_tool.assert_called_once_with(
            "test_tool",
            {"arg": "value"}
        )
        
        # Verify response contains tool result
        assert any("Tool test_tool result" in chunk for chunk in response) 