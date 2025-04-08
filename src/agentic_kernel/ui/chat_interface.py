"""Chainlit interface implementation for the chat agent."""

import logging
import json
from typing import Any, List, Dict, Optional, AsyncGenerator

# Try importing Chainlit, but allow tests to run without it
try:
    import chainlit as cl

    CHAINLIT_AVAILABLE = True
except ImportError:
    CHAINLIT_AVAILABLE = False
    cl = None

# Try importing Semantic Kernel, but allow tests to run without it
try:
    import semantic_kernel as sk
    from semantic_kernel.connectors.ai.function_choice_behavior import (
        FunctionChoiceBehavior,
    )
    from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
    from semantic_kernel.contents import ChatHistory

    SK_AVAILABLE = True
except ImportError:
    SK_AVAILABLE = False
    sk = None
    FunctionChoiceBehavior = None
    AzureChatPromptExecutionSettings = None
    ChatHistory = None

# Try importing MCP, but allow tests to run without it
try:
    from mcp import ClientSession

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = Any  # Type alias for tests

# Import necessary components from agentic_kernel
from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.config.loader import ConfigLoader
from agentic_kernel.config_types import AgentConfig
from agentic_kernel.utils.mcp_registry import MCPToolRegistry
from agentic_kernel.utils.task_manager import TaskManager
from agentic_kernel.types import Task

logger = logging.getLogger(__name__)


class ChainlitChatInterface(BaseAgent):
    """Enhanced chat agent that interfaces with Chainlit UI and the orchestration system."""

    def __init__(
        self,
        config: AgentConfig,
        kernel: Optional[sk.Kernel],
        task_manager: TaskManager,
        config_loader: Optional[ConfigLoader] = None,
    ) -> None:
        super().__init__(config=config)
        if not SK_AVAILABLE:
            raise ImportError(
                "Semantic Kernel is not available. Please install `semantic-kernel`."
            )

        self.kernel = kernel or sk.Kernel()
        self.chat_history = ChatHistory()
        self._config_loader = config_loader or ConfigLoader()
        self.mcp_registry = MCPToolRegistry()  # This agent manages its own registry
        self.task_manager = task_manager

        # Initialize chat history with system message
        self.chat_history.add_system_message(
            "I am an AI assistant that can help you with various tasks using the agentic kernel architecture. "
            "I can create and manage workflows across multiple specialized agents."
        )
        logger.info(f"ChainlitChatInterface '{config.name}' initialized.")

    def register_mcp_connection(
        self, name: str, tools: List[Dict[str, Any]], session: ClientSession
    ) -> None:
        """Register a new MCP connection."""
        self.mcp_registry.register_connection(name, tools, session)

    def unregister_mcp_connection(self, name: str) -> None:
        """Unregister an MCP connection."""
        self.mcp_registry.unregister_connection(name)

    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a task as required by the BaseAgent interface.

        For the ChatInterface, this typically means handling a user message.
        """
        message = task.parameters.get("message", "")
        user_id = task.parameters.get("user_id", "default_user")

        response_chunks = []
        async for chunk in self.handle_message(message, user_id):
            response_chunks.append(chunk)

        final_response = "".join(response_chunks)

        return {
            "status": "success",
            "response": final_response,
            "metrics": {
                "tokens": len(final_response) // 4,  # Rough estimation
                "conversation_turns": len(self.chat_history.messages) // 2,
            },
        }

    async def handle_message(
        self, message: str, user_id: str = "default_user"
    ) -> AsyncGenerator[str, None]:
        """Handle incoming chat message, interact with LLM, and handle tool calls.

        Args:
            message: The user's message content.
            user_id: The identifier for the user session.

        Yields:
            String chunks of the assistant's response.
        """
        if not CHAINLIT_AVAILABLE:
            yield "Error: Chainlit is not available."
            return

        if (
            not self.kernel
            or not FunctionChoiceBehavior
            or not AzureChatPromptExecutionSettings
        ):
            yield "Error: Semantic Kernel components not fully initialized."
            return

        try:
            # Add user message to chat history
            self.chat_history.add_user_message(message)
            logger.debug(f"Handling message from user '{user_id}': {message[:100]}...")

            # Get all available tools from the registry
            available_tools = self.mcp_registry.get_all_tools()
            logger.debug(f"Found {len(available_tools)} MCP tools for this session.")

            # Setup execution settings
            execution_settings = AzureChatPromptExecutionSettings(
                service_id="azure_openai",
                function_choice_behavior=FunctionChoiceBehavior.Auto(),
                tools=available_tools if available_tools else None,
                temperature=self.config.llm_mapping.temperature or 0.7,
                max_tokens=self.config.llm_mapping.max_tokens or 2000,
            )

            # Get Azure OpenAI service
            service = self.kernel.get_service("azure_openai")
            if not service:
                yield "Error: Azure OpenAI service not found in kernel."
                return

            # Get streaming content
            final_response_content = ""
            async with cl.Step(
                name="LLM Stream", type="llm", show_input=False
            ) as llm_step:
                llm_step.input = {
                    "chat_history_preview": str(self.chat_history)[-500:],
                    "settings": execution_settings.prepare_settings_dict(),
                    "available_tools": (
                        [t["function"]["name"] for t in available_tools]
                        if available_tools
                        else []
                    ),
                }

                try:
                    stream = service.get_streaming_chat_message_content(
                        chat_history=self.chat_history,
                        settings=execution_settings,
                        kernel=self.kernel,
                    )

                    async for chunk in stream:
                        if chunk is None:
                            continue

                        chunk_content = str(chunk)
                        final_response_content += chunk_content
                        await llm_step.stream_token(chunk_content)
                        yield chunk_content

                        # Handle tool calls
                        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                            for tool_call in chunk.tool_calls:
                                async with cl.Step(
                                    name=f"Tool Call: {tool_call.function.name}",
                                    type="tool",
                                ) as tool_step:
                                    tool_step.input = {
                                        "name": tool_call.function.name,
                                        "arguments": tool_call.function.arguments,
                                    }

                                    try:
                                        # Execute tool call
                                        tool_result = (
                                            await self.mcp_registry.execute_tool(
                                                tool_call.function.name,
                                                json.loads(
                                                    tool_call.function.arguments
                                                ),
                                            )
                                        )

                                        # Format tool result
                                        tool_response = f"\nTool {tool_call.function.name} returned: {json.dumps(tool_result, indent=2)}\n"

                                        # Add tool result to chat history
                                        self.chat_history.add_assistant_message(
                                            tool_response
                                        )

                                        # Update step and yield response
                                        tool_step.output = tool_result
                                        await llm_step.stream_token(tool_response)
                                        yield tool_response
                                        final_response_content += tool_response

                                    except Exception as e:
                                        error_msg = f"\nError executing tool {tool_call.function.name}: {str(e)}\n"
                                        tool_step.error = error_msg
                                        await llm_step.stream_token(error_msg)
                                        yield error_msg
                                        final_response_content += error_msg

                    llm_step.output = final_response_content

                except Exception as e:
                    error_msg = f"Error in LLM stream: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    llm_step.error = error_msg
                    yield f"\nError: {error_msg}\n"
                    return

            # Add final response to chat history
            self.chat_history.add_assistant_message(final_response_content)
            logger.debug(
                f"Assistant response generated: {final_response_content[:100]}..."
            )

        except Exception as e:
            error_msg = f"Error in message handling: {str(e)}"
            logger.error(error_msg, exc_info=True)
            yield f"\nError: {error_msg}\n"
