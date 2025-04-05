"""Tests for ChatAgent implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import semantic_kernel as sk
from semantic_kernel.contents import ChatHistory

from agentic_kernel.config import AgentConfig
from agentic_kernel.config.loader import ConfigLoader
from app import ChatAgent

@pytest.fixture
def mock_config_loader():
    """Create a mock ConfigLoader instance."""
    loader = MagicMock(spec=ConfigLoader)
    loader.get_model_config.return_value = {
        "temperature": 0.7,
        "max_tokens": 1000
    }
    return loader

@pytest.fixture
def mock_kernel():
    """Create a mock Semantic Kernel instance."""
    kernel = MagicMock(spec=sk.Kernel)
    return kernel

@pytest.fixture
def mock_ai_service():
    """Create a mock AI service."""
    service = AsyncMock()
    async def mock_stream(*args, **kwargs):
        yield "Test response", None
    service.get_streaming_chat_message_content = mock_stream
    return service

@pytest.fixture
def chat_agent(mock_kernel, mock_config_loader):
    """Create a ChatAgent instance for testing."""
    config = AgentConfig(
        name="test_chat_agent",
        model="gpt-4",
        endpoint="https://test.openai.azure.com/"
    )
    return ChatAgent(config=config, kernel=mock_kernel, config_loader=mock_config_loader)

def test_chat_agent_initialization(chat_agent, mock_kernel, mock_config_loader):
    """Test ChatAgent initialization."""
    assert chat_agent.kernel == mock_kernel
    assert isinstance(chat_agent.chat_history, ChatHistory)
    assert chat_agent.config.name == "test_chat_agent"
    assert chat_agent.config.model == "gpt-4"
    assert chat_agent._config_loader == mock_config_loader

@pytest.mark.asyncio
async def test_chat_history_management(chat_agent, mock_kernel, mock_ai_service):
    """Test chat history management."""
    mock_kernel.get_service.return_value = mock_ai_service
    test_message = "Hello, how are you?"
    
    # Test adding user message
    async for _ in chat_agent.handle_message(test_message):
        pass
    
    assert len(chat_agent.chat_history.messages) == 2  # User message and assistant response
    assert chat_agent.chat_history.messages[0].role == "user"
    assert chat_agent.chat_history.messages[0].content == test_message
    assert chat_agent.chat_history.messages[1].role == "assistant"
    assert chat_agent.chat_history.messages[1].content == "Test response"

@pytest.mark.asyncio
async def test_handle_message_streaming(chat_agent, mock_kernel, mock_ai_service):
    """Test message handling with streaming response."""
    mock_kernel.get_service.return_value = mock_ai_service
    test_message = "Test message"
    
    response_chunks = []
    async for chunk in chat_agent.handle_message(test_message):
        response_chunks.append(chunk)
    
    assert len(response_chunks) == 1
    assert response_chunks[0] == "Test response"
    mock_kernel.get_service.assert_called_with("azure_openai")

@pytest.mark.asyncio
async def test_handle_message_error(chat_agent, mock_kernel):
    """Test error handling in message processing."""
    mock_kernel.get_service.side_effect = Exception("Test error")
    test_message = "Test message"
    
    with pytest.raises(Exception) as exc_info:
        async for _ in chat_agent.handle_message(test_message):
            pass
    
    assert str(exc_info.value) == "Test error"

@pytest.mark.asyncio
async def test_execution_settings(chat_agent, mock_kernel, mock_ai_service):
    """Test execution settings configuration."""
    mock_kernel.get_service.return_value = mock_ai_service
    test_message = "Test message"
    
    async for _ in chat_agent.handle_message(test_message):
        pass
    
    # Verify that the service was called
    assert mock_kernel.get_service.called
    assert mock_kernel.get_service.call_args[0][0] == "azure_openai" 