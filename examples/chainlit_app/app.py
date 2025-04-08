"""Main application entry point using Semantic Kernel, Chainlit, and AgenticFleet."""

import asyncio
import os
from typing import Any, AsyncGenerator, Dict

import chainlit as cl
import semantic_kernel as sk
from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.config.loader import ConfigLoader
from agentic_kernel.config_types import AgentConfig
from agentic_kernel.orchestrator import Orchestrator
from agentic_kernel.plugins.file_surfer import FileSurferPlugin
from agentic_kernel.plugins.web_surfer import WebSurferPlugin
from agentic_kernel.types import Task, WorkflowStep
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.contents import ChatHistory

# Load configuration
config_loader = ConfigLoader()
config = config_loader.config

# Environment variables
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Get default model configuration
default_config = config.default_config
AZURE_DEPLOYMENT_NAME = default_config.get("model", "gpt-4o")


class ChatAgent(BaseAgent):
    """Chat agent implementation."""

    def __init__(self, config: AgentConfig, kernel: sk.Kernel):
        """Initialize chat agent with config and kernel."""
        self.config = config
        self.kernel = kernel
        self.chat_history = ChatHistory()

    async def handle_message(self, message: str) -> str:
        """Handle incoming chat message."""
        self.chat_history.add_user_message(message)

        execution_settings = AzureChatPromptExecutionSettings(
            service_id="azure_openai",
            function_choice_behavior=FunctionChoiceBehavior.Auto(),
        )

        # Get model configuration
        model_config = config_loader.get_model_config(
            endpoint=self.config.endpoint,
            model=self.config.model
        )

        # Update execution settings with model configuration
        for key, value in model_config.items():
            if hasattr(execution_settings, key):
                setattr(execution_settings, key, value)

        response = ""
        async for update, _ in self.kernel.get_service("azure_openai").get_streaming_chat_message_content(
            chat_history=self.chat_history,
            settings=execution_settings,
            kernel=self.kernel,
        ):
            if update is not None:
                response += str(update)
                yield str(update)

        self.chat_history.add_assistant_message(response)


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session with Semantic Kernel and AgenticFleet."""
    if not all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT]):
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
        await cl.Message(
            content=f"Failed to initialize Azure OpenAI service: {e}"
        ).send()
        return

    # Import plugins
    kernel.add_plugin(WebSurferPlugin(), plugin_name="WebSurfer")
    kernel.add_plugin(FileSurferPlugin(), plugin_name="FileSurfer")

    # Initialize chat agent
    agent_config = AgentConfig(
        name="chat_agent",
        model=AZURE_DEPLOYMENT_NAME,
        endpoint=default_config["endpoint"]
    )
    chat_agent = ChatAgent(config=agent_config, kernel=kernel)

    # Store components in session
    cl.user_session.set("kernel", kernel)
    cl.user_session.set("ai_service", ai_service)
    cl.user_session.set("chat_agent", chat_agent)

    await cl.Message(
        content="I'm ready to help! I can search the web and work with files. What would you like to do?"
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages using AgenticFleet chat agent."""
    chat_agent = cl.user_session.get("chat_agent")  # type: ChatAgent | None

    if not chat_agent:
        msg = cl.Message(content="Chat agent not initialized properly. Please restart the chat.")
        await msg.send()
        return

    # Create a Chainlit message for the response stream
    answer_msg = cl.Message(content="")

    try:
        async for content_chunk in chat_agent.handle_message(message.content):
            await answer_msg.stream_token(content_chunk)
        await answer_msg.send()  # Send only once after streaming
    except Exception as e:
        await cl.Message(
            content=f"An error occurred while processing your message: {e}"
        ).send()
        return
