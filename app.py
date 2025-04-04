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

class ChatAgent(BaseAgent):
    """Chat agent implementation."""
    
    def __init__(self, config: AgentConfig, kernel: sk.Kernel, config_loader: Optional[ConfigLoader] = None):
        super().__init__(config=config)
        self.kernel = kernel
        self.chat_history = ChatHistory()
        self._config_loader = config_loader or ConfigLoader()
        
        # Initialize chat history with system message
        self.chat_history.add_system_message(
            "I am an AI assistant that can help you with web searches, file operations, and Neon database management. "
            "I have access to various tools and can execute commands on your behalf."
        )
    
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
                                if any(t['function']['name'] == tool_call.function.name for t in tools):
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
async def start_chat():
    """Initialize the chat session based on the selected profile."""
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

    # Add Azure OpenAI Chat Completion service
    try:
        ai_service = AzureChatCompletion(
            service_id="azure_openai",
            api_key=AZURE_OPENAI_API_KEY,
            endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
            deployment_name=deployment_name,
        )
        kernel.add_service(ai_service)
        logger.info(f"Successfully initialized Azure OpenAI service with deployment {deployment_name}")
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI service with deployment {deployment_name}: {e}", exc_info=True)
        await cl.Message(
            content=f"Failed to initialize Azure OpenAI service: {e}"
        ).send()
        return

    # Store components in session
    cl.user_session.set("kernel", kernel)
    cl.user_session.set("chat_history", ChatHistory())
    cl.user_session.set("selected_profile", selected_profile)
    cl.user_session.set("deployment_name", deployment_name)
    
    profile_info = f" using the **{selected_profile}** profile" if selected_profile else ""
    await cl.Message(
        content=f"I'm ready to help{profile_info}! What would you like to do?"
    ).send()


@cl.on_message
async def on_message(msg: cl.Message):
    """Handle incoming messages."""
    chat_history = cl.user_session.get("chat_history")
    chat_history.add_user_message(msg.content)
    
    # Get kernel from session
    kernel = cl.user_session.get("kernel")
    if not kernel:
        await cl.Message(
            content="Chat session not initialized properly. Please restart the chat."
        ).send()
        return

    # Get available MCP tools
    mcp_tools = cl.user_session.get("mcp_tools", {})
    available_tools = []
    for connection_tools in mcp_tools.values():
        available_tools.extend(connection_tools)

    # Create a Chainlit message for the response stream
    answer_msg = cl.Message(content="")
    await answer_msg.send()

    try:
        execution_settings = AzureChatPromptExecutionSettings(
            service_id="azure_openai",
            function_choice_behavior=FunctionChoiceBehavior.Auto(),
            tools=available_tools if available_tools else None,
            temperature=0.7,
            top_p=0.95,
        )

        service = kernel.get_service("azure_openai")
        
        # Get streaming content
        stream = service.get_streaming_chat_message_content(
            chat_history=chat_history,
            settings=execution_settings,
            kernel=kernel
        )
        
        response = ""
        async for chunk in stream:
            if chunk is not None:
                # Check if the chunk contains a tool call
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    for tool_call in chunk.tool_calls:
                        # Find the appropriate MCP session for this tool
                        for connection_name, tools in mcp_tools.items():
                            if any(t['function']['name'] == tool_call.function.name for t in tools):
                                mcp_session = cl.user_session.get("mcp_sessions", {}).get(connection_name)
                                if mcp_session:
                                    try:
                                        # Parse tool arguments
                                        args = json.loads(tool_call.function.arguments)
                                        # Execute the tool call directly through MCP
                                        tool_result = await mcp_session.call_tool(
                                            tool_call.function.name,
                                            args
                                        )
                                        result_msg = f"\nTool {tool_call.function.name} result: {tool_result}\n"
                                        response += result_msg
                                        await answer_msg.stream_token(result_msg)
                                        
                                        # Add tool result to chat history
                                        chat_history.add_message(
                                            "assistant",
                                            f"Tool {tool_call.function.name} was called with result: {tool_result}"
                                        )
                                    except Exception as e:
                                        error_msg = f"\nError executing tool {tool_call.function.name}: {str(e)}\n"
                                        response += error_msg
                                        await answer_msg.stream_token(error_msg)
                                        logger.error(f"Tool execution error: {str(e)}", exc_info=True)
                                break
                
                response += str(chunk)
                await answer_msg.stream_token(str(chunk))
        
        chat_history.add_assistant_message(response)
        await answer_msg.update()
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        await cl.Message(
            content=f"An error occurred while processing your message: {e}"
        ).send()


@cl.on_mcp_connect
async def on_mcp(connection, session: ClientSession):
    """Called when an MCP connection is established."""
    try:
        result = await session.list_tools()
        tools = [{
            "type": "function",  # Required by Azure OpenAI
            "function": {
                "name": t.name,
                "description": t.description[:1024] if t.description else "",  # Truncate to 1024 chars
                "parameters": {
                    "type": "object",
                    "properties": t.inputSchema.get("properties", {}),
                    "required": t.inputSchema.get("required", [])
                }
            }
        } for t in result.tools]
        
        # Store tools in session
        mcp_tools = cl.user_session.get("mcp_tools", {})
        mcp_tools[connection.name] = tools
        cl.user_session.set("mcp_tools", mcp_tools)
        
        # Store session in user_session
        mcp_sessions = cl.user_session.get("mcp_sessions", {})
        mcp_sessions[connection.name] = session
        cl.user_session.set("mcp_sessions", mcp_sessions)
        
        logger.info(f"MCP connection established: {connection.name}")
        await cl.Message(f"Connected to {connection.name} MCP server with {len(tools)} tools available.").send()
    except Exception as e:
        logger.error(f"Error in on_mcp: {str(e)}", exc_info=True)
        await cl.Message(f"Error connecting to MCP server: {str(e)}").send()


@cl.on_mcp_disconnect
async def on_mcp_disconnect(name: str, session: ClientSession):
    """Called when an MCP connection is terminated."""
    try:
        # Remove tools and session
        mcp_tools = cl.user_session.get("mcp_tools", {})
        mcp_tools.pop(name, None)
        cl.user_session.set("mcp_tools", mcp_tools)
        
        mcp_sessions = cl.user_session.get("mcp_sessions", {})
        mcp_sessions.pop(name, None)
        cl.user_session.set("mcp_sessions", mcp_sessions)
        
        logger.info(f"MCP connection disconnected: {name}")
        await cl.Message(f"Disconnected from {name} MCP server.").send()
    except Exception as e:
        logger.error(f"Error in on_mcp_disconnect: {str(e)}", exc_info=True)
