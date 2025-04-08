"""Main application entry point using Chainlit and the Agentic Kernel architecture.

This module sets up the core components and connects them to the Chainlit UI handlers.
It provides:
1. Environment configuration and initialization
2. Chat agent setup with Azure OpenAI integration
3. Chainlit UI handlers for chat interaction
4. Task and progress management
5. Database interaction utilities

Typical usage:
    ```python
    # Run the Chainlit app
    chainlit run src/agentic_kernel/app.py
    ```

Dependencies:
    - chainlit: For UI and chat interface
    - semantic_kernel: For AI model integration
    - pydantic: For configuration validation
    - python-dotenv: For environment variable management
"""

import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import semantic_kernel as sk
from dotenv import load_dotenv
from pydantic import BaseModel
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory

# Try importing Chainlit, but only for the main execution block
try:
    import chainlit as cl
    from chainlit.cli import run_chainlit

    CHAINLIT_AVAILABLE = True
except ImportError:
    CHAINLIT_AVAILABLE = False
    run_chainlit = None  # Placeholder

# Import core components
from agentic_kernel.agents.chat_agent import ChatAgent
from agentic_kernel.config import ConfigLoader, env_config
from agentic_kernel.ledgers.progress_ledger import ProgressLedger
from agentic_kernel.ledgers.task_ledger import TaskLedger
from agentic_kernel.tools import MCPToolRegistry
from agentic_kernel.types import Task

# Import UI handlers - Chainlit decorators will register them automatically
from agentic_kernel.ui import handlers
from agentic_kernel.utils.task_manager import TaskManager


class EnvironmentConfig(BaseModel):
    """Configuration for the environment.

    This model validates and stores essential environment configuration for Azure OpenAI
    integration. It ensures all required fields are present and properly formatted.

    Attributes:
        azure_openai_endpoint (str): The full URL of the Azure OpenAI endpoint
        azure_openai_api_key (str): The API key for Azure OpenAI authentication
        azure_openai_api_version (str): The API version to use, defaults to latest stable

    Example:
        ```python
        config = EnvironmentConfig(
            azure_openai_endpoint="https://your-resource.openai.azure.com",
            azure_openai_api_key="your-api-key",
            azure_openai_api_version="2023-12-01-preview"
        )
        ```
    """

    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str = "2023-12-01-preview"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
logger.info(".env file loaded (if exists).")

# --- Core Initialization ---

# Initialize configuration loader globally for handlers to access
try:
    # The ConfigLoader can now potentially use env_config if needed internally
    config_loader = ConfigLoader()
    config = config_loader.config  # Keep config accessible if needed directly
    logger.info("Application configuration loaded.")
except Exception as e:
    logger.critical(f"Failed to load application configuration: {e}", exc_info=True)
    # Fallback or exit if configuration is critical
    config_loader = ConfigLoader(validate=False)  # Minimal fallback loader
    config = config_loader.config
    logger.warning("Using fallback application configuration.")

# Initialize task and progress ledgers
task_ledger = TaskLedger()
progress_ledger = ProgressLedger()

# Initialize task manager
task_manager = TaskManager(task_ledger, progress_ledger)

# Initialize environment config
env_config = EnvironmentConfig(
    azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
    azure_openai_api_version=os.getenv(
        "AZURE_OPENAI_API_VERSION", "2023-12-01-preview"
    ),
)

# Initialize agent system
agent_system = {
    "config_loader": config_loader,
    "task_manager": task_manager,
    "env_config": env_config,
}

# Store components in handlers module
handlers.config_loader = config_loader
handlers.task_manager = task_manager
handlers.agent_system = agent_system

# --- Chat Profiles ---

DEPLOYMENT_NAMES = {"Fast": "gpt-4o-mini", "Max": "gpt-4o"}
DEFAULT_DEPLOYMENT = "gpt-4o-mini"


def get_chat_profile(profile_name: Optional[str] = None) -> Dict[str, str]:
    """Get chat profile configuration based on profile name.

    This function maps profile names to specific deployment configurations. It provides
    a way to switch between different chat models based on user preferences.

    Args:
        profile_name: Optional name of the profile to use. If None or not found,
                     uses the default deployment.

    Returns:
        Dict containing profile configuration with 'model' key specifying deployment.

    Example:
        ```python
        config = get_chat_profile("Fast")  # Returns {"model": "gpt-4o-mini"}
        ```
    """
    deployment = DEPLOYMENT_NAMES.get(profile_name, DEFAULT_DEPLOYMENT)
    return {"model": deployment}


# --- Chat Handlers ---


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize chat session when a user starts chatting.

    This handler:
    1. Sets up a Semantic Kernel instance with Azure OpenAI
    2. Configures the chat agent based on user profile
    3. Stores necessary components in the session
    4. Sends a welcome message

    Raises:
        Exception: If initialization fails, logs error and notifies user
    """
    try:
        # Initialize kernel with Azure OpenAI
        kernel = sk.Kernel()

        # Get deployment name based on profile
        profile = cl.user_session.get("profile")
        chat_config = get_chat_profile(profile)

        # Add Azure OpenAI chat service using environment config
        kernel.add_service(
            "azure_openai",
            sk.connectors.ai.open_ai.AzureChatCompletion(
                service_id="azure_openai",
                deployment_name=chat_config["model"],
                endpoint=env_config.azure_openai_endpoint,
                api_key=env_config.azure_openai_api_key,
                api_version=env_config.azure_openai_api_version,
            ),
        )

        # Create chat agent with agent system
        agent = ChatAgent(
            config=config_loader.get_agent_config("chat"),
            kernel=kernel,
            config_loader=config_loader,
        )

        # Store agent and agent system in session
        cl.user_session.set("agent", agent)
        cl.user_session.set("agent_system", agent_system)

        await cl.Message(
            content=f"Chat session initialized with {profile or 'default'} profile."
        ).send()

    except Exception as e:
        logger.error(f"Failed to initialize chat session: {e}", exc_info=True)
        await cl.Message(
            content="Failed to initialize chat session. Please try again or contact support."
        ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle incoming chat messages.

    This handler processes incoming messages by:
    1. Retrieving the agent and system from session
    2. Streaming the agent's response
    3. Handling any errors gracefully

    Args:
        message: The Chainlit message object containing user input

    Raises:
        Exception: If message processing fails, logs error and notifies user
    """
    try:
        # Get agent and agent system from session
        agent = cl.user_session.get("agent")
        agent_system = cl.user_session.get("agent_system")

        if not agent or not agent_system:
            await message.send(
                content="Chat session not initialized. Please restart the chat."
            )
            return

        # Create message object
        msg = cl.Message(content="")

        # Stream response
        async for chunk in agent.handle_message(message.content):
            await msg.stream_token(chunk)

        # Send final message
        await msg.send()

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await cl.Message(
            content="An error occurred while processing your message. Please try again."
        ).send()


async def list_database_tables(message: Any) -> List[str]:
    """List all tables in the database's public schema.

    This utility function queries the database to retrieve a list of all tables
    in the public schema. It's useful for database introspection and debugging.

    Args:
        message: The Chainlit message object that triggered this request

    Returns:
        List of table names in the public schema

    Raises:
        Exception: If database query fails
    """
    try:
        async with cl.Step("Querying database tables..."):
            # Query the database for table names
            result = mcp.functions.mcp_Neon_run_sql(
                params={
                    "sql": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';",
                    "databaseName": "neondb",
                    "projectId": "dark-boat-45105135",
                }
            )

            # Check if we got a valid response with rows
            if isinstance(result, dict) and "rows" in result:
                tables = [row["table_name"] for row in result["rows"]]

                if tables:
                    # Format the table list
                    table_list = "\n".join([f"- `{table}`" for table in tables])
                    response = (
                        f"Found the following tables in the database:\n\n{table_list}\n"
                    )
                else:
                    response = "No tables found in the public schema."
            else:
                response = "No tables found or unexpected response format."

            # Send the response
            await cl.Message(content=response).send()

    except Exception as e:
        # Handle any errors that occur
        error_message = f"Error listing database tables: {str(e)}"
        await cl.Message(content=error_message).send()


# --- Main Execution ---

if __name__ == "__main__" and CHAINLIT_AVAILABLE:
    # Start Chainlit server
    run_chainlit()
