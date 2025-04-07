"""Tests for Chainlit message handlers.

This test module validates the behavior of the chat handlers in the app,
specifically focusing on the on_chat_start and on_message handlers.
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Create mock classes for Chainlit
class MockMessage:
    def __init__(self, content="", author=None):
        self.content = content
        self.author = author
        self.id = f"msg_{datetime.now().timestamp()}"
        self._tokens = []
        
    async def send(self):
        print(f"Message sent: {self.content[:30]}...")
        return self
        
    async def stream_token(self, token):
        self._tokens.append(token)
        self.content += token
        print(f"Token streamed: {token[:20]}...")
        
    async def update(self):
        print(f"Message updated: {self.content[:30]}...")

class MockStep:
    def __init__(self, name="", type=""):
        self.name = name
        self.type = type
        self.input = None
        self.output = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    async def stream_token(self, token):
        print(f"Step token: {token[:20]}...")

class MockTaskList:
    def __init__(self):
        self.tasks = []
        self.status = "Ready"
    
    async def add_task(self, task):
        self.tasks.append(task)
    
    async def send(self):
        print(f"TaskList updated: {self.status} with {len(self.tasks)} tasks")
        for task in self.tasks:
            print(f"  - {task.title}: {task.status}")

class MockTaskStatus:
    READY = "ready"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class MockTask:
    def __init__(self, title, status=None):
        self.title = title
        self.status = status
        self.forId = None

class MockChatProfile:
    def __init__(self, name, markdown_description=""):
        self.name = name
        self.markdown_description = markdown_description

# Mock user session
user_session_data = {}

class MockUserSession:
    @staticmethod
    def get(key, default=None):
        return user_session_data.get(key, default)
        
    @staticmethod
    def set(key, value):
        user_session_data[key] = value

# Create mock chainlit module
mock_cl = MagicMock()
mock_cl.Message = MockMessage
mock_cl.Step = MockStep
mock_cl.TaskList = MockTaskList
mock_cl.TaskStatus = MockTaskStatus
mock_cl.Task = MockTask
mock_cl.ChatProfile = MockChatProfile
mock_cl.user_session = MockUserSession

# Mock decorators
def mock_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator
    
mock_cl.on_chat_start = mock_decorator
mock_cl.on_message = mock_decorator
mock_cl.set_chat_profiles = mock_decorator

# Mock the chainlit module
sys.modules['chainlit'] = mock_cl

# Import app modules - patched after mocking chainlit
with patch.dict('sys.modules', {'chainlit': mock_cl}):
    from src.agentic_kernel.app import on_chat_start, on_message

# Test class for Chainlit handlers
class TestChainlitHandlers:
    """Tests for Chainlit on_chat_start and on_message handlers."""
    
    @pytest.mark.asyncio
    async def test_on_chat_start(self):
        """Test the on_chat_start handler."""
        # Set up mock user session data
        user_session_data.clear()
        user_session_data["chat_profile"] = "Fast"
        
        # Call the on_chat_start handler
        with patch('src.agentic_kernel.app.EnvironmentConfig') as mock_env_config, \
             patch('src.agentic_kernel.app.ConfigLoader') as mock_config_loader, \
             patch('src.agentic_kernel.app.sk.Kernel') as mock_kernel, \
             patch('src.agentic_kernel.app.AzureChatCompletion') as mock_azure, \
             patch('src.agentic_kernel.app.WebSurferPlugin') as mock_web_plugin, \
             patch('src.agentic_kernel.app.FileSurferPlugin') as mock_file_plugin, \
             patch('src.agentic_kernel.app.AgentConfig') as mock_agent_config, \
             patch('src.agentic_kernel.app.ChatAgent') as mock_chat_agent, \
             patch('src.agentic_kernel.app.agent_system') as mock_agent_system:
            
            # Setup mocks
            mock_kernel_instance = mock_kernel.return_value
            mock_web_plugin_instance = mock_web_plugin.return_value
            mock_file_plugin_instance = mock_file_plugin.return_value
            
            mock_agent_system.task_manager.create_task = AsyncMock()
            mock_agent_system.task_manager.update_task_status = AsyncMock()
            mock_agent_system.task_manager.sync_with_chainlit_tasklist = AsyncMock()
            
            # Call the handler
            await on_chat_start()
            
            # Verify service registration
            mock_kernel_instance.add_service.assert_called_once()
            
            # Verify plugin registration
            assert mock_kernel_instance.add_plugin.call_count == 2
            
            # Verify agent registration
            mock_agent_system.register_agent.assert_called_once()
            
            # Verify task list creation
            assert "task_list" in user_session_data
            
            # Verify startup task creation
            assert mock_agent_system.task_manager.create_task.called
            assert mock_agent_system.task_manager.update_task_status.called
    
    @pytest.mark.asyncio
    async def test_on_message(self):
        """Test the on_message handler."""
        # Set up mock user session data
        user_session_data.clear()
        
        # Create a mock TaskList and store in session
        task_list = MockTaskList()
        user_session_data["task_list"] = task_list
        
        # Create a mock chat agent
        mock_chat_agent = MagicMock()
        mock_chat_agent.handle_message = AsyncMock()
        
        # Mock response generation
        async def mock_generate_response(content, author):
            yield "First response chunk"
            yield "Second response chunk"
            
        mock_chat_agent.handle_message.side_effect = mock_generate_response
        user_session_data["chat_agent"] = mock_chat_agent
        
        # Create a test message
        test_message = MockMessage("Test query from user", "test_user")
        
        # Set up agent system mock
        with patch('src.agentic_kernel.app.agent_system') as mock_agent_system:
            mock_agent_system.task_manager.create_task = AsyncMock(return_value="test_task_id")
            mock_agent_system.task_manager.update_task_status = AsyncMock()
            
            # Call the handler
            await on_message(test_message)
            
            # Verify message handling
            mock_chat_agent.handle_message.assert_called_once_with(test_message.content)
            
            # Verify task creation and updates
            mock_agent_system.task_manager.create_task.assert_called_once()
            assert mock_agent_system.task_manager.update_task_status.call_count == 2

if __name__ == "__main__":
    # Run this directly for debugging
    pytest.main(["-xvs", __file__]) 