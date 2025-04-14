"""Main application entry point using Chainlit and the Agentic Kernel architecture.

This module sets up the core components and connects them to the Chainlit UI handlers.
It provides:
1. Environment configuration and initialization
2. Chat agent setup with Gemini integration
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
    - agentic_kernel: For AI model integration
    - pydantic: For configuration validation
    - python-dotenv: For environment variable management
"""

import logging
import os
from typing import Dict, Optional

from dotenv import load_dotenv

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
from agentic_kernel.config import (
    AgentConfig,
    AgentTeamConfig,
    ConfigLoader,
    LLMMapping,
)
from agentic_kernel.ledgers.progress_ledger import ProgressLedger
from agentic_kernel.ledgers.task_ledger import TaskLedger
from agentic_kernel.ui import handlers
from agentic_kernel.utils.task_manager import TaskManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
logger.info(".env file loaded (if exists).")

# Check for Gemini API Key
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    logger.warning("GEMINI_API_KEY environment variable not set.")
else:
    logger.info("GEMINI_API_KEY found.")

# --- Constants ---
deployment_names = {"Fast": "gemini-1.5-flash", "Max": "gemini-1.5-pro"}
default_deployment = deployment_names.get("Fast", "gemini-1.5-flash")

# --- Core Initialization ---
try:
    config_loader = ConfigLoader()
    config = config_loader.config
    logger.info("Application configuration loaded.")
except Exception as e:
    logger.critical(f"Failed to load application configuration: {e}", exc_info=True)
    config_loader = ConfigLoader(validate=False)
    config = config_loader.config
    logger.warning("Using fallback application configuration.")

# Initialize task and progress ledgers
task_ledger = TaskLedger()
progress_ledger = ProgressLedger()

# Initialize task manager
task_manager = TaskManager(task_ledger, progress_ledger)
logger.info("TaskManager initialized with task and progress ledgers.")

# Initialize agent system
agent_system = {
    "config_loader": config_loader,
    "task_manager": task_manager,
}

# Store components in handlers module
handlers.config_loader = config_loader
handlers.task_manager = task_manager
handlers.agent_system = agent_system

# Set up default team configuration if not already configured
if not config_loader.config.default_team:
    logger.info("Setting up default team configuration...")
    default_team = AgentTeamConfig(
        team_name="chat_team",
        description="Team for chat interactions",
        agents=[
            AgentConfig(
                name="chat",
                type="ChatAgent",
                description="Primary chat agent",
                llm_mapping=LLMMapping(
                    model=default_deployment,
                    endpoint="gemini",
                    temperature=0.7,
                    max_tokens=2000,
                ),
            )
        ],
    )
    config_loader.add_agent_team(default_team)
    config_loader.config.default_team = "chat_team"
    logger.info("Default team configuration added successfully.")

# --- Chat Handlers ---


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize chat session when a user starts chatting."""
    try:
        # Get deployment name based on profile
        profile = cl.user_session.get("profile")
        chat_config = get_chat_profile(profile)

        # Create chat agent with agent system
        agent = ChatAgent(
            config=config_loader.get_agent_config("chat"),
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


def get_chat_profile(profile_name: Optional[str] = None) -> Dict[str, str]:
    """Get chat profile configuration based on profile name."""
    deployment = deployment_names.get(profile_name, default_deployment)
    return {"model": deployment}


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle incoming chat messages."""
    try:
        # Get agent and agent system from session
        agent = cl.user_session.get("agent")
        agent_system = cl.user_session.get("agent_system")

        if not agent or not agent_system:
            await cl.Message(
                content="Chat session not initialized. Please restart the chat."
            ).send()
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


# --- Main Execution ---
if __name__ == "__main__" and CHAINLIT_AVAILABLE:
    # Start Chainlit server
    run_chainlit(__file__)
