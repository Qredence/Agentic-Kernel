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
from agentic_kernel.agents.base import AgentConfig, BaseAgent
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
llm_config = config_loader.llm_config

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
default_config = llm_config.default_config
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

class DynamicChatAgent(BaseAgent):
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
                            
                            response += str(chunk)
                            await llm_step.stream_token(str(chunk))
                            yield str(chunk)
                    
                    llm_step.output = response
                
                self.chat_history.add_assistant_message(response)
                step.output = response
                
        except Exception as e:
            logger.error(f"Error in handle_message: {str(e)}", exc_info=True)
            raise

# Create a global chat agent instance
chat_agent = None

@cl.on_chat_start
async def start_chat():
    """Initialize the chat session with dynamic tool support."""
    global chat_agent
    
    # Get the selected chat profile
    selected_profile = cl.user_session.get("chat_profile")
    
    # Determine deployment name based on profile
    if selected_profile in DEPLOYMENT_NAMES:
        deployment_name = DEPLOYMENT_NAMES[selected_profile]
        logger.info(f"Using deployment {deployment_name} for profile {selected_profile}")
    else:
        deployment_name = DEFAULT_DEPLOYMENT
        if selected_profile:
            logger.warning(f"Unknown profile {selected_profile}, using default deployment {deployment_name}")
        else:
            logger.warning(f"No profile selected, using default deployment {deployment_name}")
    
    # Setup Semantic Kernel
    kernel = sk.Kernel()

    try:
        # Add Azure OpenAI Chat Completion service
        ai_service = AzureChatCompletion(
            service_id="azure_openai",
            api_key=AZURE_OPENAI_API_KEY,
            endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
            deployment_name=deployment_name,
        )
        kernel.add_service(ai_service)
        
        # Initialize the chat agent
        config = AgentConfig(
            name=f"AgenticFleet-{selected_profile}" if selected_profile else "AgenticFleet",
            endpoint=AZURE_OPENAI_ENDPOINT,
            model=deployment_name
        )
        chat_agent = DynamicChatAgent(config=config, kernel=kernel, config_loader=config_loader)
        
        # Store in session
        cl.user_session.set("chat_agent", chat_agent)
        cl.user_session.set("selected_profile", selected_profile)
        
        profile_info = f" using the **{selected_profile}** profile" if selected_profile else ""
        await cl.Message(
            content=f"I'm ready to help{profile_info}! I'll adapt to any tools that become available."
        ).send()
        
    except Exception as e:
        error_msg = f"Failed to initialize chat agent: {e}"
        logger.error(error_msg, exc_info=True)
        await cl.Message(content=error_msg).send()
        return

@cl.on_message
async def on_message(msg: cl.Message):
    """Handle incoming messages with dynamic tool support."""
    chat_agent = cl.user_session.get("chat_agent")
    if not chat_agent:
        await cl.Message(
            content="Chat session not initialized properly. Please restart the chat."
        ).send()
        return

    async with cl.Step(name="Message Processing", type="system") as step:
        step.input = msg.content
        
        # Create a Chainlit message for the response stream
        answer_msg = cl.Message(content="")
        await answer_msg.send()

        try:
            async for content in chat_agent.handle_message(msg.content):
                await answer_msg.stream_token(content)
            
            await answer_msg.update()
            step.output = "Message processed successfully"
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg, exc_info=True)
            step.output = error_msg
            await answer_msg.update()
            raise

@cl.on_mcp_connect
async def on_mcp(connection, session: ClientSession):
    """Register new MCP connection and its tools."""
    try:
        result = await session.list_tools()
        tools = [{
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description[:1024] if t.description else "",
                "parameters": {
                    "type": "object",
                    "properties": t.inputSchema.get("properties", {}),
                    "required": t.inputSchema.get("required", [])
                }
            }
        } for t in result.tools]
        
        # Get chat agent from session
        chat_agent = cl.user_session.get("chat_agent")
        if chat_agent:
            # Register the new connection
            chat_agent.register_mcp_connection(connection.name, tools, session)
            
            logger.info(f"MCP connection established: {connection.name}")
            await cl.Message(
                f"Connected to {connection.name} MCP server with {len(tools)} tools available. "
                "I can now use these tools to assist you!"
            ).send()
    except Exception as e:
        logger.error(f"Error in on_mcp: {str(e)}", exc_info=True)
        await cl.Message(f"Error connecting to MCP server: {str(e)}").send()

@cl.on_mcp_disconnect
async def on_mcp_disconnect(name: str, session: ClientSession):
    """Handle MCP connection termination."""
    try:
        # Get chat agent from session
        chat_agent = cl.user_session.get("chat_agent")
        if chat_agent:
            # Unregister the connection
            chat_agent.unregister_mcp_connection(name)
        
        logger.info(f"MCP connection disconnected: {name}")
        await cl.Message(
            f"Disconnected from {name} MCP server. Related tools are no longer available."
        ).send()
    except Exception as e:
        logger.error(f"Error in on_mcp_disconnect: {str(e)}", exc_info=True)

async def list_database_tables(msg: cl.Message):
    """List all tables in the database with detailed steps."""
    async with cl.Step(name="Database Tables", type="database", show_input=True) as step:
        step.input = "Fetching all tables from public schema"
        
        try:
            # Execute the SQL query
            async with cl.Step(name="Execute SQL", type="sql", show_input=True) as sql_step:
                sql_step.input = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
                
                result = await mcp_Neon_run_sql(params={
                    "sql": sql_step.input,
                    "databaseName": "neondb",
                    "projectId": "dark-boat-45105135"
                })
                
                sql_step.output = result
            
            # Format the results
            if result and isinstance(result, list):
                tables = [row.get("table_name") for row in result if row.get("table_name")]
                if tables:
                    response = "Found the following tables in the database:\n\n"
                    for table in tables:
                        response += f"- `{table}`\n"
                else:
                    response = "No tables found in the public schema."
            else:
                response = "No tables found or unexpected response format."
            
            step.output = response
            
            # Send the formatted response
            await cl.Message(content=response).send()
            
        except Exception as e:
            error_msg = f"Error listing database tables: {str(e)}"
            step.output = error_msg
            await cl.Message(content=error_msg).send()
            logger.error(error_msg, exc_info=True)
