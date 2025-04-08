"""Chainlit event handlers for the Agentic Kernel application."""

import logging
from typing import List, Optional, Any

# Try importing Chainlit, but allow tests to run without it
try:
    import chainlit as cl
    from chainlit.types import ThreadDict

    CHAINLIT_AVAILABLE = True
except ImportError:
    CHAINLIT_AVAILABLE = False
    cl = None
    ThreadDict = dict  # Type alias for tests

# Try importing Semantic Kernel, but allow tests to run without it
try:
    import semantic_kernel as sk
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

    SK_AVAILABLE = True
except ImportError:
    SK_AVAILABLE = False
    sk = None
    AzureChatCompletion = None

# Try importing MCP, but allow tests to run without it
try:
    from mcp import ClientSession

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = Any  # Type alias for tests

# Import necessary components from agentic_kernel
from agentic_kernel.config.loader import ConfigLoader
from agentic_kernel.config_types import AgentConfig
from agentic_kernel.agents.web_surfer_agent import WebSurferAgent
from agentic_kernel.agents.file_surfer_agent import FileSurferAgent
from agentic_kernel.config.agent_team import LLMMapping
from agentic_kernel.systems.agent_system import AgentSystem
from agentic_kernel.ui.chat_interface import ChainlitChatInterface

logger = logging.getLogger(__name__)

# Define deployment names for different profiles (consider moving to a config file)
DEPLOYMENT_NAMES = {
    "Fast": "gpt-4o-mini",
    "Max": "gpt-4o",
}
DEFAULT_DEPLOYMENT = DEPLOYMENT_NAMES["Fast"]

# Global variables for agent system and chat interface (managed within handlers)
agent_system: Optional[AgentSystem] = None
chat_interface: Optional[ChainlitChatInterface] = None


def initialize_agent_system(loader: ConfigLoader) -> AgentSystem:
    """Initialize the AgentSystem instance."""
    global agent_system
    if agent_system is None:
        try:
            agent_system = AgentSystem(loader)
            logger.info("AgentSystem initialized within handlers.")
        except Exception as e:
            logger.error(
                f"Failed to initialize AgentSystem in handlers: {e}", exc_info=True
            )
            raise
    return agent_system


@cl.set_chat_profiles
async def chat_profile() -> List[cl.ChatProfile]:
    """Define the available chat profiles for the application."""
    if not CHAINLIT_AVAILABLE:
        return []
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


@cl.on_chat_start
async def start_chat() -> None:
    """Initialize the chat session with the full agent system."""
    global chat_interface, agent_system

    if not CHAINLIT_AVAILABLE:
        logger.error("Chainlit not available, cannot start chat.")
        return

    if not SK_AVAILABLE:
        await cl.Message(
            content="Error: Semantic Kernel is required but not installed."
        ).send()
        return

    try:
        # Get agent system from user session
        agent_system = cl.user_session.get("agent_system")
        if not agent_system:
            await cl.Message(content="Error: Agent system not initialized.").send()
            return

        # Get the selected chat profile
        selected_profile = cl.user_session.get("chat_profile")
        deployment_name = DEPLOYMENT_NAMES.get(selected_profile, DEFAULT_DEPLOYMENT)
        logger.info(
            f"Starting chat with profile: {selected_profile or 'Fast'} (Deployment: {deployment_name})"
        )

        # Setup Semantic Kernel
        kernel = sk.Kernel()
        env_config = agent_system["env_config"]
        ai_service = AzureChatCompletion(
            service_id="azure_openai",
            api_key=env_config.azure_openai_api_key,
            endpoint=env_config.azure_openai_endpoint,
            api_version=env_config.azure_openai_api_version,
            deployment_name=deployment_name,
        )
        kernel.add_service(ai_service)

        # Initialize chat interface
        agent_config = AgentConfig(
            name="chat_interface",
            type="ChatInterface",
            description="Main chat interface agent for user interaction",
            llm_mapping=LLMMapping(
                model=deployment_name,
                endpoint="azure_openai",  # Should match service_id used in kernel
            ),
            config={},
        )

        chat_interface = ChainlitChatInterface(
            config=agent_config,
            kernel=kernel,
            task_manager=agent_system["task_manager"],
            config_loader=agent_system["config_loader"],
        )

        # Store chat interface in user session
        cl.user_session.set("chat_interface", chat_interface)
        logger.info("Chat interface stored in user session.")

        # Initialize TaskList visualization for TaskLedger
        task_list = cl.TaskList()
        task_list.status = "Initializing"
        cl.user_session.set("task_list", task_list)

        # Send the TaskList to the UI
        await task_list.send()

        # Sync any existing tasks from the TaskLedger with the TaskList
        await agent_system["task_manager"].sync_with_chainlit_tasklist(task_list)

        # Create a system initialization task to show in the task list
        startup_task_id = await agent_system["task_manager"].create_task(
            agent_type="system",
            name="system_initialization",
            description="Initialize the agent system and load plugins",
            params={"profile": selected_profile or "Fast"},
        )

        # Mark the initialization task as completed
        await agent_system["task_manager"].update_task_status(
            startup_task_id, "completed", {"message": "System initialized successfully"}
        )

        # Update the task list to show the completed initialization
        await agent_system["task_manager"].sync_with_chainlit_tasklist(task_list)

        # Welcome message
        await cl.Message(
            content=(
                "👋 Hello! I'm your agentic assistant powered by the Agentic Kernel architecture.\n\n"
                "I can help you with various tasks including:\n"
                "- Web searches and information retrieval\n"
                "- File operations and data processing\n"
                "- Multi-step workflow execution\n"
                "- Database operations\n\n"
                "What would you like to do today?"
            )
        ).send()

    except Exception as e:
        error_msg = f"Failed to initialize chat session: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await cl.Message(content=f"Error: {error_msg}").send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle incoming chat messages."""
    try:
        # Get chat interface from session
        chat_interface = cl.user_session.get("chat_interface")
        if not chat_interface:
            await cl.Message(content="Error: Chat interface not initialized.").send()
            return

        # Create message object
        msg = cl.Message(content="")

        # Stream response
        async for chunk in chat_interface.handle_message(message.content):
            await msg.stream_token(chunk)

        # Send final message
        await msg.send()

    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await cl.Message(content=f"Error: {error_msg}").send()


@cl.on_mcp_connect
async def on_mcp(connection: Any, session: ClientSession) -> None:
    """Handle MCP connection."""
    if not MCP_AVAILABLE:
        return
    try:
        # Store MCP session in user session
        cl.user_session.set("mcp_session", session)
        logger.info("MCP session stored in user session.")
    except Exception as e:
        logger.error(f"Error handling MCP connection: {e}", exc_info=True)


@cl.on_mcp_disconnect
async def on_mcp_disconnect(name: str, session: ClientSession) -> None:
    """Handle MCP disconnection."""
    if not MCP_AVAILABLE:
        return
    try:
        # Remove MCP session from user session
        cl.user_session.pop("mcp_session", None)
        logger.info("MCP session removed from user session.")
    except Exception as e:
        logger.error(f"Error handling MCP disconnection: {e}", exc_info=True)


# Note: list_database_tables removed as it seems like a specific debug/test function.
# If needed, it should likely be implemented as a proper tool/plugin.
