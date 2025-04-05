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
from typing import Optional, AsyncGenerator, Dict, Any, List, Callable
import json
import importlib

from agentic_kernel.config.loader import ConfigLoader
from agentic_kernel.config import AgentConfig, LLMMapping
from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.plugins.web_surfer import WebSurferPlugin
from agentic_kernel.plugins.file_surfer import FileSurferPlugin

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
config = config_loader.config

# Environment variables
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEON_MCP_TOKEN = os.getenv("NEON_MCP_TOKEN")

# Define deployment names for different profiles
DEPLOYMENT_NAMES = {
    "Fast": "gpt-4o-mini",  # Fast profile uses gpt-4o-mini
    "Max": "gpt-4o",        # Max profile uses gpt-4o
}

# Get default model configuration
default_config = config.default_model
DEFAULT_DEPLOYMENT = "gpt-4o-mini"  # Changed default to Fast profile's model

@cl.set_chat_profiles
async def chat_profile():
    """Define the available chat profiles for the application."""
    return [
        cl.ChatProfile(
            name="Fast",
            markdown_description="Uses **gpt-4o-mini** for faster responses with good quality.",
        ),
        cl.ChatProfile(
            name="Max",
            markdown_description="Uses **gpt-4o** for maximum quality responses.",
        ),
    ]

class MCPToolRegistry:
    """Registry for MCP tools and their handlers."""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, ClientSession] = {}
        
    def register_connection(self, name: str, tools: List[Dict], session: ClientSession):
        """Register a new MCP connection with its tools."""
        self.tools[name] = tools
        self.sessions[name] = session
        
    def unregister_connection(self, name: str):
        """Unregister an MCP connection."""
        self.tools.pop(name, None)
        self.sessions.pop(name, None)
        
    def get_all_tools(self) -> List[Dict]:
        """Get all registered tools across all connections."""
        all_tools = []
        for tools in self.tools.values():
            all_tools.extend(tools)
        return all_tools
    
    def get_session_for_tool(self, tool_name: str) -> Optional[tuple[str, ClientSession]]:
        """Get the session that can handle a specific tool."""
        for connection_name, tools in self.tools.items():
            if any(t['function']['name'] == tool_name for t in tools):
                return connection_name, self.sessions[connection_name]
        return None
    
    def is_empty(self) -> bool:
        """Check if there are any registered tools."""
        return len(self.tools) == 0

class ChatAgent(BaseAgent):
    """Enhanced chat agent with dynamic MCP tool support."""
    
    def __init__(self, config: AgentConfig, kernel: sk.Kernel, config_loader: Optional[ConfigLoader] = None):
        super().__init__(config=config)
        self.kernel = kernel
        self.chat_history = ChatHistory()
        self._config_loader = config_loader or ConfigLoader()
        self.mcp_registry = MCPToolRegistry()
        
        # Initialize chat history with system message
        self.chat_history.add_system_message(
            "I am an AI assistant that can help you with various tasks using available tools. "
            "My capabilities adapt based on the tools that are connected."
        )
    
    def register_mcp_connection(self, name: str, tools: List[Dict], session: ClientSession):
        """Register a new MCP connection."""
        self.mcp_registry.register_connection(name, tools, session)
        
    def unregister_mcp_connection(self, name: str):
        """Unregister an MCP connection."""
        self.mcp_registry.unregister_connection(name)
    
    async def handle_message(self, message: str) -> AsyncGenerator[str, None]:
        """Handle incoming chat message with dynamic tool support."""
        try:
            async with cl.Step(name="Process Message", type="agent") as step:
                step.input = message
                self.chat_history.add_user_message(message)
                
                # Get all available tools
                available_tools = self.mcp_registry.get_all_tools()
                
                execution_settings = AzureChatPromptExecutionSettings(
                    service_id="azure_openai",
                    function_choice_behavior=FunctionChoiceBehavior.Auto(),
                    tools=available_tools if available_tools else None
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
                service = self.kernel.get_service("azure_openai")
                
                # Get streaming content
                async with cl.Step(name="LLM Stream", type="llm", show_input=True) as llm_step:
                    llm_step.input = {
                        "chat_history": str(self.chat_history),
                        "settings": str(execution_settings),
                        "available_tools": [t['function']['name'] for t in available_tools] if available_tools else []
                    }
                    
                    stream = service.get_streaming_chat_message_content(
                        chat_history=self.chat_history,
                        settings=execution_settings,
                        kernel=self.kernel
                    )
                    
                    async for chunk in stream:
                        if chunk is not None:
                            # Handle tool calls dynamically
                            if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                                for tool_call in chunk.tool_calls:
                                    # Find the appropriate session for this tool
                                    session_info = self.mcp_registry.get_session_for_tool(tool_call.function.name)
                                    if session_info:
                                        connection_name, session = session_info
                                        try:
                                            async with cl.Step(name=f"Tool: {tool_call.function.name}", type="tool", show_input=True) as tool_step:
                                                args = json.loads(tool_call.function.arguments)
                                                tool_step.input = args
                                                
                                                tool_result = await session.call_tool(
                                                    tool_call.function.name,
                                                    args
                                                )
                                                tool_step.output = tool_result
                                                response += f"\nTool {tool_call.function.name} result: {tool_result}\n"
                                                yield f"\nTool {tool_call.function.name} result: {tool_result}\n"
                                        except Exception as e:
                                            error_msg = f"\nError executing tool {tool_call.function.name}: {str(e)}\n"
                                            response += error_msg
                                            yield error_msg
                            else:
                                # Handle regular text content
                                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                                if content:
                                    response += content
                                    yield content
                
                # Add assistant's response to chat history
                self.chat_history.add_assistant_message(response)
                
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg)
            yield error_msg

@cl.on_chat_start
async def on_chat_start():
    """Initialize chat session."""
    try:
        # Check for required environment variables
        if not all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT]):
            msg = "Required environment variables (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT) are not set."
            await cl.Message(content=msg).send()
            return

        # Initialize kernel with Azure OpenAI service
        kernel = sk.Kernel()
        
        # Get the selected profile or use default
        profile = cl.user_session.get("chat_profile")
        deployment = DEPLOYMENT_NAMES.get(profile, DEFAULT_DEPLOYMENT)
        
        # Configure Azure OpenAI service
        azure_chat_service = AzureChatCompletion(
            deployment_name=deployment,
            endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        kernel.add_service("azure_openai", azure_chat_service)
        
        # Create chat agent with selected profile configuration
        agent_config = AgentConfig(
            name="chat_agent",
            type="ChatAgent",
            description="A chat agent that helps users with various tasks",
            llm_mapping=LLMMapping(
                model=deployment,
                endpoint="azure_openai"
            )
        )
        chat_agent = ChatAgent(config=agent_config, kernel=kernel)
        
        # Store components in session
        cl.user_session.set("kernel", kernel)
        cl.user_session.set("ai_service", azure_chat_service)
        cl.user_session.set("chat_agent", chat_agent)
        
        # Send welcome message
        welcome_msg = (
            "👋 Hello! I'm your AI assistant. I can help you with various tasks.\n\n"
            "💡 I'm powered by Azure OpenAI and can adapt my capabilities based on the tools available."
        )
        await cl.Message(content=welcome_msg).send()
        
    except Exception as e:
        error_msg = f"Error initializing chat: {str(e)}"
        logger.error(error_msg)
        await cl.Message(content=error_msg).send()

@cl.on_message
async def on_message(msg: cl.Message):
    """Handle incoming chat messages."""
    try:
        chat_agent = cl.user_session.get("chat_agent")
        if not chat_agent:
            await cl.Message(
                content="Chat agent not initialized properly. Please restart the chat."
            ).send()
            return
        
        response = cl.Message(content="")
        async for chunk in chat_agent.handle_message(msg.content):
            await response.stream_token(chunk)
        
        await response.send()
        
    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        logger.error(error_msg)
        await cl.Message(content=error_msg).send()

@cl.on_mcp_connect
async def on_mcp(connection, session: ClientSession):
    """Handle MCP connection and register tools."""
    try:
        chat_agent = cl.user_session.get("chat_agent")
        if not chat_agent:
            logger.warning("Chat agent not found in session during MCP connection")
            return
        
        # Register the connection and its tools with the chat agent
        chat_agent.register_mcp_connection(
            name=connection.name,
            tools=connection.tools,
            session=session
        )
        
        # Notify user about new capabilities
        tool_names = [t['function']['name'] for t in connection.tools]
        msg = (
            f"✨ Connected to {connection.name}!\n\n"
            f"New capabilities added:\n"
            f"- " + "\n- ".join(tool_names)
        )
        await cl.Message(content=msg).send()
        
    except Exception as e:
        error_msg = f"Error handling MCP connection: {str(e)}"
        logger.error(error_msg)
        await cl.Message(content=error_msg).send()

@cl.on_mcp_disconnect
async def on_mcp_disconnect(name: str, session: ClientSession):
    """Handle MCP disconnection."""
    try:
        chat_agent = cl.user_session.get("chat_agent")
        if chat_agent:
            chat_agent.unregister_mcp_connection(name)
            
        msg = f"🔌 Disconnected from {name}. Related capabilities have been removed."
        await cl.Message(content=msg).send()
        
    except Exception as e:
        error_msg = f"Error handling MCP disconnection: {str(e)}"
        logger.error(error_msg)
        await cl.Message(content=error_msg).send()

@cl.action_callback("list_tables")
async def list_database_tables(msg: cl.Message):
    """List tables in the connected database."""
    try:
        chat_agent = cl.user_session.get("chat_agent")
        if not chat_agent:
            await cl.Message(content="Chat agent not initialized.").send()
            return
        
        # Check if we have database tools available
        if chat_agent.mcp_registry.is_empty():
            await cl.Message(content="No database connection available.").send()
            return
        
        # Use the chat agent to handle the request
        response = cl.Message(content="")
        async for chunk in chat_agent.handle_message("List all tables in the database"):
            await response.stream_token(chunk)
        
        await response.send()
        
    except Exception as e:
        error_msg = f"Error listing database tables: {str(e)}"
        logger.error(error_msg)
        await cl.Message(content=error_msg).send() 