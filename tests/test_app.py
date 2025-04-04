"""Tests for the main application."""
import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from semantic_kernel.contents import ChatHistory
import chainlit as cl
import semantic_kernel as sk
from agenticfleet.config.loader import ConfigLoader
from agenticfleet.agents.base import AgentConfig
from agenticfleet.app import ChatAgent, on_chat_start, on_message, chat_profile

class AsyncIterator:
    """Helper class to create an async iterator."""
    def __init__(self, items):
        self.items = items
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)

@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    with patch.dict(os.environ, {
        'AZURE_OPENAI_API_KEY': 'test_key',
        'AZURE_OPENAI_ENDPOINT': 'test_endpoint',
        'AZURE_OPENAI_API_VERSION': '2024-02-15-preview',
        'GEMINI_API_KEY': 'test_gemini_key'
    }):
        yield

@pytest.fixture
def mock_config():
    """Mock LLM configuration."""
    config = MagicMock()
    config.default_config = {
        'endpoint': 'azure_openai',
        'model': 'gpt-4o',
        'temperature': 0.7
    }
    return config

@pytest.fixture
def mock_config_loader(mock_config):
    """Mock ConfigLoader."""
    with patch('agenticfleet.app.ConfigLoader') as mock:
        mock.return_value.llm_config = mock_config
        mock.return_value.get_model_config.return_value = {
            'temperature': 0.7,
            'max_tokens': 4096,
            'endpoint': 'azure_openai',
            'endpoint_type': 'azure_openai'
        }
        yield mock

@pytest.fixture
def mock_kernel():
    """Mock Semantic Kernel."""
    kernel = MagicMock(spec=sk.Kernel)
    service = MagicMock()
    service.get_streaming_chat_message_content = AsyncMock(
        return_value=AsyncIterator([("Hello", None)])
    )
    kernel.get_service.return_value = service
    return kernel

@pytest.fixture
def mock_chainlit():
    """Mock Chainlit session and message."""
    with patch('chainlit.user_session') as mock_session:
        mock_session.set = MagicMock()
        mock_session.get = MagicMock()
        yield mock_session

@pytest.fixture
def mock_chainlit_context():
    """Mock Chainlit context."""
    context = MagicMock()
    context.session = MagicMock()
    with patch('chainlit.context.context_var') as mock_var:
        mock_var.get.return_value = context
        yield context

class TestChatAgent:
    """Test ChatAgent class."""
    
    @pytest.mark.asyncio
    async def test_init(self):
        """Test ChatAgent initialization."""
        config = AgentConfig(
            name="test_agent",
            model="gpt-4o",
            endpoint="azure_openai"
        )
        kernel = MagicMock()
        agent = ChatAgent(config=config, kernel=kernel)
        
        assert agent.config == config
        assert agent.kernel == kernel
        assert isinstance(agent.chat_history, ChatHistory)
    
    @pytest.mark.asyncio
    async def test_handle_message(self, mock_kernel, mock_config_loader):
        """Test ChatAgent handle_message method."""
        config = AgentConfig(
            name="test_agent",
            model="gpt-4o",
            endpoint="azure_openai"
        )
        agent = ChatAgent(config=config, kernel=mock_kernel)
        
        response = []
        async for chunk in agent.handle_message("test message"):
            response.append(chunk)
        
        assert response == ["Hello"]
        assert len(agent.chat_history.messages) == 2  # User message + Assistant response

@pytest.mark.asyncio
async def test_on_chat_start_success(mock_env_vars, mock_config_loader, mock_chainlit, mock_chainlit_context):
    """Test successful chat initialization."""
    mock_message = AsyncMock()
    with patch('chainlit.Message', return_value=mock_message):
        await on_chat_start()
    
    # Verify components were stored in session
    assert mock_chainlit.set.call_count == 3
    mock_chainlit.set.assert_any_call("kernel", mock_chainlit.set.call_args_list[0][0][1])
    mock_chainlit.set.assert_any_call("ai_service", mock_chainlit.set.call_args_list[1][0][1])
    mock_chainlit.set.assert_any_call("chat_agent", mock_chainlit.set.call_args_list[2][0][1])

@pytest.mark.asyncio
async def test_on_chat_start_missing_env_vars(mock_chainlit_context):
    """Test chat initialization with missing environment variables."""
    mock_message = AsyncMock()
    with patch('chainlit.Message', return_value=mock_message):
        with patch.dict(os.environ, {}, clear=True):
            await on_chat_start()
    
    mock_message.send.assert_called_once()
    assert "not set" in mock_message.content

@pytest.mark.asyncio
async def test_on_message_success(mock_chainlit, mock_chainlit_context):
    """Test successful message handling."""
    # Setup mock chat agent
    mock_agent = MagicMock()
    mock_agent.handle_message = AsyncMock(
        return_value=AsyncIterator(["Hello"])
    )
    mock_chainlit.get.return_value = mock_agent
    
    # Setup mock message
    mock_message = AsyncMock(content="test message")
    mock_response = AsyncMock()
    
    with patch('chainlit.Message', return_value=mock_response):
        await on_message(mock_message)
    
    mock_response.send.assert_called_once()
    mock_response.stream_token.assert_called_with("Hello")

@pytest.mark.asyncio
async def test_on_message_no_agent(mock_chainlit, mock_chainlit_context):
    """Test message handling with no agent."""
    mock_chainlit.get.return_value = None
    mock_message = AsyncMock()
    mock_response = AsyncMock()
    mock_response.content = "Chat agent not initialized properly. Please restart the chat."
    
    with patch('chainlit.Message', return_value=mock_response):
        await on_message(mock_message)
    
    mock_response.send.assert_called_once()
    assert "not initialized" in mock_response.content

@pytest.mark.asyncio
async def test_chat_profile():
    """Test chat profile configuration."""
    profiles = await chat_profile()
    assert len(profiles) == 2
    
    # Test Fast profile
    fast_profile = next((p for p in profiles if p.name == "Fast"), None)
    assert fast_profile is not None
    assert "gpt-4o-mini" in fast_profile.markdown_description.lower()
    
    # Test Max profile
    max_profile = next((p for p in profiles if p.name == "Max"), None)
    assert max_profile is not None
    assert "gpt-4o" in max_profile.markdown_description.lower()

@pytest.mark.asyncio
async def test_on_chat_start_with_fast_profile(mock_env_vars, mock_config_loader, mock_chainlit, mock_chainlit_context):
    """Test chat initialization with Fast profile."""
    # Mock the chat profile selection
    mock_chainlit.get.side_effect = lambda key: "Fast" if key == "chat_profile" else None
    
    mock_message = AsyncMock()
    with patch('chainlit.Message', return_value=mock_message):
        await on_chat_start()
    
    # Verify the correct model was selected
    mock_config_loader.return_value.get_model_config.assert_called_with(
        endpoint="azure_openai",
        model="gpt-4o-mini"
    )
    
    # Verify welcome message contains profile info
    assert "Fast" in mock_message.content
    mock_message.send.assert_called_once()

@pytest.mark.asyncio
async def test_on_chat_start_with_max_profile(mock_env_vars, mock_config_loader, mock_chainlit, mock_chainlit_context):
    """Test chat initialization with Max profile."""
    # Mock the chat profile selection
    mock_chainlit.get.side_effect = lambda key: "Max" if key == "chat_profile" else None
    
    mock_message = AsyncMock()
    with patch('chainlit.Message', return_value=mock_message):
        await on_chat_start()
    
    # Verify the correct model was selected
    mock_config_loader.return_value.get_model_config.assert_called_with(
        endpoint="azure_openai",
        model="gpt-4o"
    )
    
    # Verify welcome message contains profile info
    assert "Max" in mock_message.content
    mock_message.send.assert_called_once()

@pytest.mark.asyncio
async def test_on_chat_start_with_invalid_profile(mock_env_vars, mock_config_loader, mock_chainlit, mock_chainlit_context):
    """Test chat initialization with invalid profile."""
    # Mock an invalid chat profile selection
    mock_chainlit.get.side_effect = lambda key: "Invalid" if key == "chat_profile" else None
    
    mock_message = AsyncMock()
    with patch('chainlit.Message', return_value=mock_message):
        await on_chat_start()
    
    # Verify fallback to default configuration
    mock_config_loader.return_value.get_model_config.assert_called_with(
        endpoint="azure_openai",
        model="gpt-4o"  # Default model
    )
    
    # Verify error message
    assert "Unknown chat profile" in mock_message.content
    mock_message.send.assert_called() 