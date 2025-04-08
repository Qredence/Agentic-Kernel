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
    .. code-block:: python

        # Initialize the chat agent
        config = AgentConfig(temperature=0.7, max_tokens=1000)
        client = AsyncAzureOpenAI(...)
        agent = ChatAgent(config, client)
        
        # Execute a chat task
        task = Task(
            description="Tell me about Python",
            agent_type="chat"
        )
        result = await agent.execute(task)
        print(result['output'])
"""

from typing import Dict, Any, Optional, AsyncGenerator, List
import logging
from openai import AsyncAzureOpenAI

from ..config.loader import ConfigLoader
from ..config_types import AgentConfig
from ..types import Task
from ..types import TaskStatus as Status
from ..exceptions import TaskExecutionError
from .base import BaseAgent, TaskCapability
from ..tools import MCPToolRegistry

logger = logging.getLogger(__name__)


class ChatAgent(BaseAgent):
    """Agent for handling interactive chat sessions.

    This agent specializes in managing interactive chat sessions using Azure OpenAI's
    chat models. It supports streaming responses, maintains chat history, and can
    integrate with external tools through the MCP Tool Registry.

    The agent uses OpenAI's client for model interaction and supports configurable
    parameters like temperature and max tokens for response generation.

    Attributes:
        client (AsyncAzureOpenAI): OpenAI client for model interaction.
        config_loader (Optional[ConfigLoader]): Loader for dynamic configuration.
        chat_history (List[Dict]): Tracks conversation history.
        mcp_registry (MCPToolRegistry): Registry for available tools.

    Example:
        .. code-block:: python

            # Create a chat agent
            client = AsyncAzureOpenAI(
                api_key="your-key",
                api_version="2023-12-01-preview",
                azure_endpoint="your-endpoint"
            )

            agent = ChatAgent(
                config=AgentConfig(temperature=0.7),
                client=client
            )

            # Stream a response
            async for chunk in agent.handle_message("Hello!"):
                print(chunk, end="")
    """

    def __init__(
        self,
        config: AgentConfig,
        client: AsyncAzureOpenAI,
        config_loader: Optional[ConfigLoader] = None,
    ) -> None:
        """Initialize the chat agent.

        Args:
            config (AgentConfig): Configuration parameters for the agent.
            client (AsyncAzureOpenAI): OpenAI client instance.
            config_loader (Optional[ConfigLoader]): Optional loader for dynamic configuration updates.
        """
        super().__init__(config)
        self.client = client
        self.config_loader = config_loader
        self.chat_history: List[Dict] = []
        self.mcp_registry = MCPToolRegistry()

    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a chat task.

        This method processes a chat task by streaming the response and
        collecting it into a single result. It handles errors gracefully
        and returns a structured result.

        Args:
            task (Task): Task containing the chat message in its description.

        Returns:
            Dict[str, Any]: Dictionary containing:

            - status: "success" or "failure"
            - output: Complete response text if successful
            - error: Error message if failed

        Example:
            .. code-block:: python

                task = Task(
                    description="What is Python?",
                    agent_type="chat"
                )
                result = await agent.execute(task)
                if result['status'] == 'success':
                    print(result['output'])
                else:
                    print(f"Error: {result['error']}")
        """
        try:
            response: List[str] = []
            async for chunk in self.handle_message(task.description):
                response.append(chunk)

            return {"status": Status.completed, "output": "".join(response)}
        except Exception as e:
            logger.error(f"Chat task execution failed: {str(e)}", exc_info=True)
            return {"status": "failed", "error": str(e), "output": None}

    async def handle_message(self, message: str) -> AsyncGenerator[str, None]:
        """Handle a chat message and stream the response.

        This method processes a single chat message by:
        1. Adding it to the chat history
        2. Getting a streaming response from the model
        3. Yielding response chunks
        4. Updating the chat history with the complete response

        Args:
            message (str): The user's chat message.

        Yields:
            str: Response chunks as they're received from the model.

        Raises:
            TaskExecutionError: If message processing fails.

        Example:
            .. code-block:: python

                async for chunk in agent.handle_message("Hello!"):
                    print(chunk, end="", flush=True)
        """
        try:
            # Add user message to history
            self.chat_history.append({"role": "user", "content": message})

            # Stream response
            stream = await self.client.chat.completions.create(
                model=self.config.llm_mapping.model,
                messages=self.chat_history,
                temperature=self.config.llm_mapping.temperature,
                max_tokens=self.config.llm_mapping.max_tokens,
                stream=True
            )

            response_chunks: List[str] = []
            
            async for chunk in stream:
                # Check if chunk has choices and delta content
                if (hasattr(chunk, 'choices') and 
                    len(chunk.choices) > 0 and 
                    hasattr(chunk.choices[0], 'delta') and 
                    hasattr(chunk.choices[0].delta, 'content') and 
                    chunk.choices[0].delta.content):
                    response_chunks.append(chunk.choices[0].delta.content)
                    yield chunk.choices[0].delta.content

            # Add complete response to history if we got any chunks
            complete_response = "".join(response_chunks)
            if complete_response:
                self.chat_history.append({"role": "assistant", "content": complete_response})
            else:
                logger.warning("Received empty response from model")
                self.chat_history.append({"role": "assistant", "content": "I apologize, but I received an empty response. Could you please try again?"})
                yield "I apologize, but I received an empty response. Could you please try again?"

        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}", exc_info=True)
            raise TaskExecutionError(f"Message processing failed: {str(e)}")

    def _get_supported_tasks(self) -> Dict[str, TaskCapability]:
        """Get the tasks supported by this agent.

        Returns:
            Dict[str, TaskCapability]: Mapping of task types to their capabilities.
        """
        return {
            "chat": TaskCapability(
                description="Handle interactive chat messages",
                parameters=["message"],
                returns=["response"],
            )
        }
