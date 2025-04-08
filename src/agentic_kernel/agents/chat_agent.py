"""Chat agent implementation for handling interactive chat sessions.

This module provides a specialized agent for managing interactive chat sessions
using Azure OpenAI's chat models. It handles message streaming, history tracking,
and tool integration.

Key features:
1. Streaming chat responses
2. Chat history management
3. Tool integration via MCPToolRegistry
4. Temperature and token control
5. Error handling and recovery

Example:
    ```python
    # Initialize the chat agent
    config = AgentConfig(temperature=0.7, max_tokens=1000)
    kernel = sk.Kernel()
    agent = ChatAgent(config, kernel)
    
    # Execute a chat task
    task = Task(
        description="Tell me about Python",
        agent_type="chat"
    )
    result = await agent.execute(task)
    print(result['output'])
    ```
"""

from typing import Dict, Any, Optional, AsyncGenerator, List
import logging
import semantic_kernel as sk
from semantic_kernel.contents import ChatHistory
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)

from ..config.loader import ConfigLoader
from ..config_types import AgentConfig
from ..types import Task, TaskStatus
from ..exceptions import TaskExecutionError
from .base import BaseAgent, TaskCapability
from ..tools import MCPToolRegistry

logger = logging.getLogger(__name__)


class ChatAgent(BaseAgent):
    """Agent for handling interactive chat sessions.

    This agent specializes in managing interactive chat sessions using Azure OpenAI's
    chat models. It supports streaming responses, maintains chat history, and can
    integrate with external tools through the MCP Tool Registry.

    The agent uses Semantic Kernel for model interaction and supports configurable
    parameters like temperature and max tokens for response generation.

    Attributes:
        kernel (sk.Kernel): Semantic Kernel instance for model interaction
        config_loader (Optional[ConfigLoader]): Loader for dynamic configuration
        chat_history (ChatHistory): Tracks conversation history
        mcp_registry (MCPToolRegistry): Registry for available tools

    Example:
        ```python
        # Create a chat agent
        kernel = sk.Kernel()
        kernel.add_service(
            "azure_openai",
            sk.azure_chat_service(deployment="gpt-4")
        )

        agent = ChatAgent(
            config=AgentConfig(temperature=0.7),
            kernel=kernel
        )

        # Stream a response
        async for chunk in agent.handle_message("Hello!"):
            print(chunk, end="")
        ```
    """

    def __init__(
        self,
        config: AgentConfig,
        kernel: sk.Kernel,
        config_loader: Optional[ConfigLoader] = None,
    ) -> None:
        """Initialize the chat agent.

        Args:
            config: Configuration parameters for the agent
            kernel: Semantic Kernel instance with chat service configured
            config_loader: Optional loader for dynamic configuration updates

        Raises:
            ValueError: If kernel doesn't have a chat service configured
        """
        super().__init__(config)
        self.kernel = kernel
        self.config_loader = config_loader
        self.chat_history = ChatHistory()
        self.mcp_registry = MCPToolRegistry()

        # Verify chat service is configured
        if not self.kernel.get_service("azure_openai"):
            raise ValueError("Kernel must have azure_openai service configured")

    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a chat task.

        This method processes a chat task by streaming the response and
        collecting it into a single result. It handles errors gracefully
        and returns a structured result.

        Args:
            task: Task containing the chat message in its description

        Returns:
            Dictionary containing:
            - status: "success" or "failure"
            - output: Complete response text if successful
            - error: Error message if failed

        Example:
            ```python
            task = Task(
                description="What is Python?",
                agent_type="chat"
            )
            result = await agent.execute(task)
            if result['status'] == 'success':
                print(result['output'])
            else:
                print(f"Error: {result['error']}")
            ```
        """
        try:
            response: List[str] = []
            async for chunk in self.handle_message(task.description):
                response.append(chunk)

            return {"status": TaskStatus.completed, "output": "".join(response)}
        except Exception as e:
            logger.error(f"Chat task execution failed: {str(e)}", exc_info=True)
            return {"status": TaskStatus.failed, "error": str(e), "output": None}

    async def handle_message(self, message: str) -> AsyncGenerator[str, None]:
        """Handle a chat message and stream the response.

        This method processes a single chat message by:
        1. Adding it to the chat history
        2. Getting a streaming response from the model
        3. Yielding response chunks
        4. Updating the chat history with the complete response

        Args:
            message: The user's chat message

        Yields:
            Response chunks as they're received from the model

        Raises:
            TaskExecutionError: If message processing fails

        Example:
            ```python
            async for chunk in agent.handle_message("Hello!"):
                print(chunk, end="", flush=True)
            ```
        """
        try:
            # Add user message to history
            self.chat_history.add_user_message(message)

            # Get chat service
            chat_service = self.kernel.get_service("azure_openai")

            # Collect response chunks
            response_chunks: List[str] = []

            # Stream response
            async for chunk in chat_service.get_streaming_chat_message_content(
                self.chat_history,
                execution_settings=AzureChatPromptExecutionSettings(
                    service_id=chat_service.service_id,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    function_choice_behavior=FunctionChoiceBehavior.AUTO,
                ),
            ):
                response_chunks.append(chunk)
                yield chunk

            # Add complete response to history
            complete_response = "".join(response_chunks)
            self.chat_history.add_assistant_message(complete_response)

        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}", exc_info=True)
            raise TaskExecutionError(f"Chat message processing failed: {str(e)}")

    def _get_supported_tasks(self) -> Dict[str, TaskCapability]:
        """Get the tasks supported by this agent.

        Returns:
            Dictionary mapping task types to their capabilities

        Example:
            ```python
            capabilities = agent._get_supported_tasks()
            print(capabilities['chat']['description'])
            ```
        """
        return {
            "chat": {
                "description": "Process chat messages and generate responses",
                "parameters": ["message"],
                "optional_parameters": ["temperature", "max_tokens"],
                "examples": [
                    {
                        "message": "Tell me about Python",
                        "temperature": 0.7,
                        "max_tokens": 1000,
                    }
                ],
            }
        }
