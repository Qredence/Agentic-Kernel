"""Main application entry point using Semantic Kernel, Chainlit, and AgenticFleet."""

import os
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import chainlit as cl
from mcp import ClientSession
import semantic_kernel as sk
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.contents import ChatHistory
from typing import Optional, AsyncGenerator, Dict, Any, List
import json

from agenticfleet.config.loader import ConfigLoader
from agenticfleet.agents.base import AgentConfig, BaseAgent
from agenticfleet.plugins.web_surfer import WebSurferPlugin
from agenticfleet.plugins.file_surfer import FileSurferPlugin

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
config_loader = ConfigLoader()
llm_config = config_loader.llm_config

# Environment variables
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEON_MCP_TOKEN = os.getenv("NEON_MCP_TOKEN")

# Get default model configuration
default_config = llm_config.default_config
AZURE_DEPLOYMENT_NAME = default_config.get("model", "gpt-4o")


class ChatAgent(BaseAgent):
    """Chat agent implementation."""
    
    def __init__(self, config: AgentConfig, kernel: sk.Kernel, config_loader: Optional[ConfigLoader] = None):
        super().__init__(config=config)
        self.kernel = kernel
        self.chat_history = ChatHistory()
        self._config_loader = config_loader or ConfigLoader()
    
    async def handle_message(self, message: str) -> AsyncGenerator[str, None]:
        """Handle incoming chat message.
        
        Args:
            message: The user's message
            
        Yields:
            Content updates from the LLM response
            
        Raises:
            Exception: If there is an error processing the message
        """
        try:
            self.chat_history.add_user_message(message)
            
            # Get available MCP tools
            mcp_tools = cl.user_session.get("mcp_tools", {})
            available_tools = []
            for connection_tools in mcp_tools.values():
                available_tools.extend(connection_tools)
            
            execution_settings = AzureChatPromptExecutionSettings(
                service_id="azure_openai",
                function_choice_behavior=FunctionChoiceBehavior.Auto(),
                tools=available_tools if available_tools else None
            )
            
            # Get model configuration
            model_config = self._config_loader.get_model_config(
                endpoint=self.config.endpoint,
                model=self.config.model
            )
            
            # Update execution settings with model configuration
            for key, value in model_config.items():
                if hasattr(execution_settings, key):
                    setattr(execution_settings, key, value)
            
            response = ""
            service = self.kernel.get_service("azure_openai")
            
            # Get streaming content
            stream = service.get_streaming_chat_message_content(
                chat_history=self.chat_history,
                settings=execution_settings,
                kernel=self.kernel
            )
            
            async for chunk in stream:
                if chunk is not None:
                    # Check if the chunk contains a tool call
                    if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                        for tool_call in chunk.tool_calls:
                            # Find the appropriate MCP session for this tool
                            for connection_name, tools in mcp_tools.items():
                                if any(t['name'] == tool_call.function.name for t in tools):
                                    mcp_session = cl.user_session.get("mcp_sessions", {}).get(connection_name)
                                    if mcp_session:
                                        try:
                                            # Parse tool arguments
                                            args = json.loads(tool_call.function.arguments)
                                            # Execute the tool call
                                            tool_result = await mcp_session.call_tool(
                                                tool_call.function.name,
                                                args
                                            )
                                            response += f"\nTool {tool_call.function.name} result: {tool_result}\n"
                                            yield f"\nTool {tool_call.function.name} result: {tool_result}\n"
                                        except Exception as e:
                                            error_msg = f"\nError executing tool {tool_call.function.name}: {str(e)}\n"
                                            response += error_msg
                                            yield error_msg
                                    break
                    
                    response += str(chunk)
                    yield str(chunk)
            
            self.chat_history.add_assistant_message(response)
        except Exception as e:
            logger.error(f"Error in handle_message: {str(e)}", exc_info=True)
            raise


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session with Semantic Kernel and AgenticFleet."""
    if not all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT]):
        logger.warning("Azure OpenAI environment variables are not set")
        await cl.Message(
            content="Azure OpenAI environment variables (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT) are not set. Please configure them."
        ).send()
        return

    # Setup Semantic Kernel
    kernel = sk.Kernel()

    # Add Azure OpenAI Chat Completion service
    try:
        ai_service = AzureChatCompletion(
            service_id="azure_openai",
            api_key=AZURE_OPENAI_API_KEY,
            endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
            deployment_name=AZURE_DEPLOYMENT_NAME,
        )
        kernel.add_service(ai_service)
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI service: {e}", exc_info=True)
        await cl.Message(
            content=f"Failed to initialize Azure OpenAI service: {e}"
        ).send()
        return

    # Import plugins
    kernel.add_plugin(WebSurferPlugin(), plugin_name="WebSurfer")
    kernel.add_plugin(FileSurferPlugin(), plugin_name="FileSurfer")

    # Initialize MCP session for Neon
    if NEON_MCP_TOKEN:
        try:
            # Start the MCP server in a separate terminal
            await cl.Message(
                content="Please start the MCP server in a separate terminal with:\n```bash\nnpx -y @neondatabase/mcp-server-neon start " + NEON_MCP_TOKEN + "\n```"
            ).send()
            
            # Wait for user confirmation
            await cl.Message(
                content="After starting the MCP server, the tools will be available for use."
            ).send()
            
            # Store MCP tools
            mcp_tools = {"neon": [
                {
                    "name": "mcp_Neon_list_projects",
                    "description": "List all Neon projects in your account."
                },
                {
                    "name": "mcp_Neon_create_project",
                    "description": "Create a new Neon project."
                },
                {
                    "name": "mcp_Neon_delete_project",
                    "description": "Delete a Neon project"
                },
                {
                    "name": "mcp_Neon_describe_project",
                    "description": "Describes a Neon project"
                },
                {
                    "name": "mcp_Neon_run_sql",
                    "description": "Execute a single SQL statement against a Neon database"
                }
            ]}
            cl.user_session.set("mcp_tools", mcp_tools)
            
            logger.info(f"MCP tools registered")
        except Exception as e:
            logger.error(f"Failed to initialize MCP session: {e}", exc_info=True)
            await cl.Message(
                content=f"Failed to initialize MCP session: {e}"
            ).send()

    # Initialize chat agent
    agent_config = AgentConfig(
        name="chat_agent",
        model=AZURE_DEPLOYMENT_NAME,
        endpoint=default_config["endpoint"]
    )
    chat_agent = ChatAgent(config=agent_config, kernel=kernel, config_loader=config_loader)

    # Store components in session
    cl.user_session.set("kernel", kernel)
    cl.user_session.set("ai_service", ai_service)
    cl.user_session.set("chat_agent", chat_agent)
    
    logger.info("Chat session initialized successfully")
    await cl.Message(
        content="I'm ready to help! I can search the web, work with files, and interact with your Neon database. What would you like to do?"
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages using AgenticFleet chat agent."""
    chat_agent = cl.user_session.get("chat_agent")  # type: ChatAgent | None

    if not chat_agent:
        await cl.Message(
            content="Chat agent not initialized properly. Please restart the chat."
        ).send()
        return

    # Create a Chainlit message for the response stream
    answer_msg = cl.Message(content="")
    await answer_msg.send()

    try:
        async for content_chunk in chat_agent.handle_message(message.content):
            await answer_msg.stream_token(content_chunk)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        await cl.Message(
            content=f"An error occurred while processing your message: {e}"
        ).send()
        return

    await answer_msg.update()


@cl.on_mcp_connect
async def on_mcp_connect(connection, session: ClientSession):
    """Called when an MCP connection is established."""
    try:
        # List available tools
        result = await session.list_tools()
        
        # Process tool metadata
        tools = [{
            "name": t.name,
            "description": t.description,
            "input_schema": t.inputSchema,
        } for t in result.tools]
        
        # Store tools for later use
        mcp_tools = cl.user_session.get("mcp_tools", {})
        mcp_tools[connection.name] = tools
        cl.user_session.set("mcp_tools", mcp_tools)
        
        logger.info(f"MCP connection established: {connection.name}")
    except Exception as e:
        logger.error(f"Error in MCP connection: {str(e)}", exc_info=True)
        raise

@cl.on_mcp_disconnect
async def on_mcp_disconnect(name: str, session: ClientSession):
    """Called when an MCP connection is terminated."""
    try:
        # Clean up stored tools
        mcp_tools = cl.user_session.get("mcp_tools", {})
        if name in mcp_tools:
            del mcp_tools[name]
        cl.user_session.set("mcp_tools", mcp_tools)
        
        logger.info(f"MCP connection terminated: {name}")
    except Exception as e:
        logger.error(f"Error in MCP disconnection: {str(e)}", exc_info=True)
