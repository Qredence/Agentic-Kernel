"""Chat agent implementation for handling interactive chat sessions.

This module provides a specialized agent for managing interactive chat sessions
using Google Gemini's chat models. It handles message streaming, history tracking,
and tool integration.

Key features:
1. Streaming chat responses
2. Chat history management
3. Tool integration via StandardToolRegistry
4. Temperature and token control
5. Error handling and recovery

Example:
    .. code-block:: python

        # Initialize the chat agent
        config = AgentConfig(temperature=0.7, max_tokens=1000)
        agent = ChatAgent(config)

        # Execute a chat task
        task = Task(
            description="Tell me about Python",
            agent_type="chat"
        )
        result = await agent.execute(task)
        print(result['output'])
"""

# Standard library imports
from collections.abc import AsyncGenerator
import logging
import os
from typing import Any

# Third-party imports
import google.generativeai as genai

# First-party/local application imports
from .base import BaseAgent
from ..config.loader import ConfigLoader
from ..config_types import AgentConfig
from ..tools import StandardToolRegistry
from ..types import Task, TaskStatus as Status

logger = logging.getLogger(__name__)


class ChatAgent(BaseAgent):
    """An agent designed for interactive chat sessions using Gemini API.

    This agent maintains a chat history and interacts with the Gemini API
    to generate responses based on the conversation context.
    It supports streaming responses back to the user.

    Attributes:
        config (AgentConfig): Configuration specific to this agent.
        tool_registry (StandardToolRegistry): Registry for available tools.
        chat_history (list[dict[str, str]]): History of the conversation.
        model (genai.GenerativeModel): The initialized Gemini model instance.
    """

    def __init__(
        self,
        config: AgentConfig,
        config_loader: ConfigLoader | None = None,
        tool_registry: StandardToolRegistry | None = None,
    ) -> None:
        """Initializes the ChatAgent.

        Args:
            config: Configuration specific to this agent.
            config_loader: Optional configuration loader.
            tool_registry: Optional tool registry.

        Raises:
            ValueError: If GEMINI_API_KEY environment variable is not set.
        """
        super().__init__(config) # Pass only config
        self.config_loader = config_loader # Store config_loader
        self.tool_registry = tool_registry # Store tool_registry
        self.chat_history: list[dict[str, Any]] = [] # Use Any for parts later

        # Configure Gemini API Key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable not set.")
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        genai.configure(api_key=api_key)

        # Initialize Gemini Model
        model_name = self.config.llm_mapping.model
        logger.info(f"Initializing Gemini model: {model_name}")
        self.model = genai.GenerativeModel(model_name)

        # TODO: Add system prompt/initial history if needed from config
        # self.chat_history.append({...})

    async def execute(self, task: Task) -> dict[str, Any]:
        """Execute a chat task.

        This method processes a chat task by streaming the response and
        collecting it into a single result. It handles errors gracefully
        and returns a structured result.

        Args:
            task (Task): Task containing the chat message in its description.

        Returns:
            dict[str, Any]: Dictionary containing:

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
            response: list[str] = []
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
            message: The user's message.

        Yields:
            str: Chunks of the response message from the AI model.

        Example:
            ```python
            # Assuming 'agent' is an initialized ChatAgent instance
            async def stream_response():
                async for chunk in agent.handle_message("Hello!"):
                    print(chunk, end="", flush=True)

            # Run the async function
            import asyncio
            asyncio.run(stream_response())
            ```
        """
        try:
            # Adapt history format for Gemini API (role: user/model, parts: [text])
            gemini_history = [
                {"role": "model" if msg["role"] == "assistant" else "user", "parts": [msg["content"]]}
                for msg in self.chat_history
            ]
            # Add current user message
            gemini_history.append({"role": "user", "parts": [message]})

            # Add user message to internal history *before* API call
            self.chat_history.append({"role": "user", "content": message})

            logger.debug(f"Sending message to Gemini model {self.model.model_name}")
            response_chunks = []
            # Call Gemini API
            stream = await self.model.generate_content_async(
                gemini_history,
                stream=True,
                generation_config=genai.types.GenerationConfig(),
            )

            async for chunk in stream:
                if chunk.parts:
                    response_text = chunk.parts[0].text
                    response_chunks.append(response_text)
                    yield response_text # Yield text part of the chunk

            # Add complete response to history if we got any chunks
            complete_response = "".join(response_chunks)
            if complete_response:
                self.chat_history.append(
                    {"role": "assistant", "content": complete_response},
                )
            else:
                logger.warning("Received empty response from model")
                self.chat_history.append(
                    {"role": "assistant", "content": "<empty response>"},
                )

        except Exception as e:
            logger.error(f"Error during Gemini API call: {e}", exc_info=True)
            # Add error placeholder to history
            self.chat_history.append({"role": "assistant", "content": f"<Error: {e}>"})
            yield f"An error occurred: {e}" # Yield error message to user

    @classmethod
    def get_capabilities(cls) -> dict[str, Any]:
        """Get the capabilities of this agent.
        
        Returns:
            A dictionary describing the agent's capabilities.
        """
        return {
            "type": "chat",
            "supported_tasks": {
                "chat": {
                    "description": "Interactive chat session with streaming responses",
                    "parameters": ["message"],
                    "optional_parameters": ["context", "history"],
                    "examples": [
                        {"message": "Hello, how can you help me?"},
                        {"message": "What's the weather like?", "context": {"location": "San Francisco"}},
                    ],
                },
            },
            "config": {
                "model": "Gemini model for natural language chat",
                "streaming": True,
                "history_enabled": True,
            },
        }
        
    def _get_supported_tasks(self) -> dict[str, Any]:
        """Get the tasks supported by this agent.
        
        Returns:
            Dict[str, TaskCapability]: Dictionary mapping task types to their capabilities.
        """
        return {
            "chat": {
                "description": "Interactive chat session with streaming responses",
                "parameters": ["message"],
                "optional_parameters": ["context", "history"],
                "examples": [
                    {"message": "Hello, how can you help me?"},
                    {"message": "What's the weather like?", "context": {"location": "San Francisco"}},
                ],
            },
        }
