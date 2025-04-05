"""Tests for the main application."""
import os
from unittest.mock import AsyncMock, MagicMock, patch, ANY
import pytest
from semantic_kernel.contents import ChatHistory
import chainlit as cl
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from agentic_kernel.config.loader import ConfigLoader
from agentic_kernel.config import AgentConfig, LLMMapping
from agentic_kernel.app import ChatAgent, on_chat_start, on_message, chat_profile, MCPToolRegistry
from agentic_kernel.types import Task
from typing import Dict, Any as TypingAny, AsyncGenerator, Optional
from agentic_kernel.agents.base import BaseAgent
import asyncio

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
    env_vars = {
        "AZURE_OPENAI_ENDPOINT": "https://test-endpoint",
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_API_VERSION": "2024-02-15-preview",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "test-deployment",
        "AZURE_OPENAI_SERVICE_ID": "test-service-id"
    }
    with patch.dict('os.environ', env_vars):
        yield env_vars

@pytest.fixture
def mock_config():
    """Mock LLM configuration."""
    config = MagicMock()
    config.default_model = {
        'endpoint': 'azure_openai',
        'model': 'gpt-4o-mini',
        'temperature': 0.7
    }
    return config

@pytest.fixture
def mock_config_loader():
    """Mock config loader fixture."""
    mock = MagicMock(spec=ConfigLoader)
    mock.get_model_config.return_value = {
        "name": "test_agent",
        "type": "ChatAgent",
        "description": "A test chat agent",
        "llm_mapping": {
            "model": "gpt-4o-mini",
            "endpoint": "azure_openai"
        },
        "temperature": 0.7,
        "max_tokens": 1000
    }
    return mock

@pytest.fixture
def mock_kernel():
    """Mock kernel fixture."""
    mock = MagicMock(spec=sk.Kernel)
    
    async def mock_stream():
        yield "Hello"
    
    mock_service = MagicMock()
    mock_service.get_streaming_chat_message_content.return_value = mock_stream()
    mock.get_service.return_value = mock_service
    return mock

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def setup_chainlit_context():
    """Setup Chainlit context for tests."""
    from chainlit.context import init_http_context
    context = init_http_context()
    yield context

@pytest.fixture
def mock_chainlit():
    """Mock chainlit session fixture."""
    with patch('chainlit.user_session') as mock_session:
        mock_session.set = MagicMock()
        mock_session.get = MagicMock()
        yield mock_session

@pytest.fixture
def mock_chainlit_context():
    """Mock chainlit context fixture."""
    with patch('chainlit.context') as mock_context:
        mock_context.session = MagicMock()
        yield mock_context

@pytest.fixture
def mock_message():
    """Mock message fixture."""
    mock = AsyncMock()
    mock.content = "test message"
    mock.send = AsyncMock()
    mock.stream_token = AsyncMock()
    return mock

@pytest.fixture
def mock_azure_service():
    """Mock Azure OpenAI service fixture."""
    with patch('semantic_kernel.connectors.ai.open_ai.AzureChatCompletion') as mock_service:
        mock_instance = MagicMock()
        mock_instance.service_id = "test-service-id"
        mock_instance.deployment_name = "test-deployment"
        mock_instance.endpoint = "https://test-endpoint"
        mock_instance.api_key = "test-key"
        mock_instance.api_version = "2024-02-15-preview"
        mock_service.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_semantic_kernel():
    """Mock semantic kernel fixture."""
    with patch('semantic_kernel.Kernel') as mock_kernel:
        mock_instance = MagicMock()
        mock_kernel.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_deployment_names():
    """Mock deployment names fixture."""
    deployment_names = {
        "Fast": "gpt-4o-mini",
        "Max": "gpt-4o"
    }
    with patch('src.agentic_kernel.app.DEPLOYMENT_NAMES', deployment_names):
        with patch('src.agentic_kernel.app.DEFAULT_DEPLOYMENT', "gpt-4o-mini"):
            yield deployment_names

class TestChatAgent:
    """Test cases for ChatAgent class."""

    def test_init(self, mock_kernel, mock_config_loader):
        """Test ChatAgent initialization."""
        config = AgentConfig(
            name="test_agent",
            type="ChatAgent",
            description="Test chat agent for unit tests",
            llm_mapping=LLMMapping(
                model="gpt-4o",
                endpoint="azure_openai"
            )
        )
        agent = ChatAgent(config=config, kernel=mock_kernel, config_loader=mock_config_loader)
        
        assert agent.config == config
        assert agent.kernel == mock_kernel
        assert isinstance(agent.chat_history, ChatHistory)
        assert isinstance(agent.mcp_registry, MCPToolRegistry)

    @pytest.mark.asyncio
    async def test_handle_message(self, mock_kernel, mock_config_loader):
        """Test ChatAgent handle_message method."""
        config = AgentConfig(
            name="test_agent",
            type="ChatAgent",
            description="Test chat agent for unit tests",
            llm_mapping=LLMMapping(
                model="gpt-4o",
                endpoint="azure_openai"
            )
        )
        agent = ChatAgent(config=config, kernel=mock_kernel, config_loader=mock_config_loader)
        
        response = []
        async for chunk in agent.handle_message("test message"):
            response.append(chunk)
        
        assert "".join(response) == "Hello"
        assert len(agent.chat_history.messages) == 2  # System message + user message

@pytest.mark.asyncio
async def test_on_chat_start_success(
    mock_env_vars,
    mock_config_loader,
    mock_chainlit,
    mock_chainlit_context,
    mock_message,
    mock_azure_service,
    mock_semantic_kernel,
    mock_deployment_names
):
    """Test successful chat initialization."""
    with patch('chainlit.Message', return_value=mock_message):
        await on_chat_start()

    # Verify components were stored in session
    assert mock_chainlit.set.call_count == 3
    mock_chainlit.set.assert_any_call("kernel", ANY)
    mock_chainlit.set.assert_any_call("ai_service", ANY)
    mock_chainlit.set.assert_any_call("chat_agent", ANY)

@pytest.mark.asyncio
async def test_on_chat_start_with_fast_profile(
    mock_env_vars,
    mock_config_loader,
    mock_chainlit,
    mock_chainlit_context,
    mock_message,
    mock_azure_service,
    mock_semantic_kernel,
    mock_deployment_names
):
    """Test chat initialization with Fast profile."""
    # Mock the chat profile selection
    mock_chainlit.get.return_value = "Fast"

    with patch('chainlit.Message', return_value=mock_message):
        await on_chat_start()

    # Verify components were stored in session
    assert mock_chainlit.set.call_count == 3
    mock_chainlit.set.assert_any_call("kernel", ANY)
    mock_chainlit.set.assert_any_call("ai_service", ANY)
    mock_chainlit.set.assert_any_call("chat_agent", ANY)

@pytest.mark.asyncio
async def test_on_chat_start_with_max_profile(
    mock_env_vars,
    mock_config_loader,
    mock_chainlit,
    mock_chainlit_context,
    mock_message,
    mock_azure_service,
    mock_semantic_kernel,
    mock_deployment_names
):
    """Test chat initialization with Max profile."""
    # Mock the chat profile selection
    mock_chainlit.get.return_value = "Max"

    with patch('chainlit.Message', return_value=mock_message):
        await on_chat_start()

    # Verify components were stored in session
    assert mock_chainlit.set.call_count == 3
    mock_chainlit.set.assert_any_call("kernel", ANY)
    mock_chainlit.set.assert_any_call("ai_service", ANY)
    mock_chainlit.set.assert_any_call("chat_agent", ANY)

@pytest.mark.asyncio
async def test_on_chat_start_with_invalid_profile(
    mock_env_vars,
    mock_config_loader,
    mock_chainlit,
    mock_chainlit_context,
    mock_message,
    mock_azure_service,
    mock_semantic_kernel,
    mock_deployment_names
):
    """Test chat initialization with invalid profile."""
    # Mock an invalid chat profile selection
    mock_chainlit.get.return_value = "Invalid"

    with patch('chainlit.Message', return_value=mock_message):
        await on_chat_start()

    # Verify components were stored in session with default configuration
    assert mock_chainlit.set.call_count == 3
    mock_chainlit.set.assert_any_call("kernel", ANY)
    mock_chainlit.set.assert_any_call("ai_service", ANY)
    mock_chainlit.set.assert_any_call("chat_agent", ANY)

@pytest.mark.asyncio
async def test_on_message_success(mock_chainlit, mock_chainlit_context, mock_message):
    """Test successful message handling."""
    # Setup mock chat agent
    mock_agent = MagicMock()
    async def mock_handle_message(*args, **kwargs):
        yield "Hello"
    mock_agent.handle_message = mock_handle_message
    mock_chainlit.get.return_value = mock_agent

    # Setup mock message
    user_message = AsyncMock(content="test message")
    response_message = mock_message

    with patch('chainlit.Message', return_value=response_message):
        await on_message(user_message)

    response_message.stream_token.assert_called_with("Hello")
    response_message.send.assert_called_once()

@pytest.mark.asyncio
async def test_on_message_no_agent(mock_chainlit, mock_chainlit_context, mock_message):
    """Test message handling with no agent."""
    mock_chainlit.get.return_value = None
    user_message = AsyncMock(content="test message")
    response_message = mock_message
    response_message.content = "Chat agent not initialized properly. Please restart the chat."

    with patch('chainlit.Message', return_value=response_message):
        await on_message(user_message)

    response_message.send.assert_called_once()
    assert "not initialized" in response_message.content

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

class MockChatAgent(BaseAgent):
    """Mock chat agent for testing."""
    async def execute(self, task):
        """Mock execute method."""
        return {"status": "success", "output": "test output"}

@pytest.fixture
def mock_chat_agent():
    """Mock chat agent fixture."""
    with patch('src.agentic_kernel.app.ChatAgent', MockChatAgent):
        yield

class ChatAgent(BaseAgent):
    """Chat agent implementation."""

    def __init__(self, config: AgentConfig, kernel: sk.Kernel, config_loader: Optional[ConfigLoader] = None):
        """Initialize chat agent with config and kernel."""
        super().__init__(config=config)
        self.kernel = kernel
        self.chat_history = ChatHistory()
        self._config_loader = config_loader or ConfigLoader()
        self.mcp_registry = MCPToolRegistry()

    async def execute(self, task: Task) -> Dict[str, TypingAny]:
        """Execute a task.
        
        Args:
            task: Task object containing the task details
            
        Returns:
            Dictionary containing task execution results
        """
        try:
            response = []
            async for chunk in self.handle_message(task.parameters.get("message", "")):
                response.append(chunk)
            return {
                "status": "success",
                "result": "".join(response)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def handle_message(self, message: str) -> AsyncGenerator[str, None]:
        """Handle incoming chat message."""
        self.chat_history.add_user_message(message)

        execution_settings = AzureChatPromptExecutionSettings(
            service_id="azure_openai",
            function_choice_behavior=FunctionChoiceBehavior.Auto(),
        )

        # Get model configuration
        model_config = self._config_loader.get_model_config(
            endpoint=self.config.llm_mapping.endpoint,
            model=self.config.llm_mapping.model
        )

        # Update execution settings with model configuration
        for key, value in model_config.items():
            if hasattr(execution_settings, key):
                setattr(execution_settings, key, value)

        response = ""
        stream = self.kernel.get_service("azure_openai").get_streaming_chat_message_content(
            chat_history=self.chat_history,
            settings=execution_settings,
            kernel=self.kernel,
        )
        
        async for update in stream:
            if update is not None:
                response += str(update)
                yield str(update)

        self.chat_history.add_assistant_message(response) 