"""Main application entry point using Mesop and the Agentic Kernel architecture.

This module sets up the core components and connects them to the Mesop UI handlers.
It provides:
1. Environment configuration and initialization
2. Chat agent setup with Gemini integration
3. Mesop UI handlers for chat interaction
4. Task and progress management

Typical usage:
    ```python
    # Run the Mesop app
    python -m src.agentic_kernel.mesop_app
    ```

Dependencies:
    - mesop: For UI and chat interface
    - agentic_kernel: For AI model integration
    - python-dotenv: For environment variable management
    - google-generativeai: For Gemini API integration
"""

import logging
import os
from typing import Dict, Optional

import mesop as mp
from dotenv import load_dotenv
from mesop.components import button, container, markdown, text_area, text_input

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

# --- Application State ---
class AppState:
    """Application state for the Mesop UI."""
    
    def __init__(self):
        self.messages = []
        self.agent = None
        self.is_processing = False
        
    def initialize_agent(self):
        """Initialize the chat agent."""
        if self.agent is None:
            try:
                self.agent = ChatAgent(
                    config=config_loader.get_agent_config("chat"),
                    config_loader=config_loader,
                )
                logger.info("Chat agent initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize chat agent: {e}", exc_info=True)
                return False
        return True

# Create application state
app_state = AppState()

# --- Mesop UI Handlers ---
async def handle_send_message(message: str):
    """Handle sending a message to the agent."""
    if not message.strip():
        return
    
    # Initialize agent if not already done
    if not app_state.initialize_agent():
        app_state.messages.append({"role": "system", "content": "Failed to initialize chat agent. Please check logs."})
        return
    
    # Add user message to UI
    app_state.messages.append({"role": "user", "content": message})
    app_state.is_processing = True
    
    # Process with agent
    try:
        full_response = ""
        async for chunk in app_state.agent.handle_message(message):
            full_response += chunk
            # Update the UI with the current response
            app_state.messages[-1] = {"role": "assistant", "content": full_response}
            mp.update()
        
        # Ensure the final response is added
        if not full_response:
            app_state.messages.append({"role": "assistant", "content": "No response received from the agent."})
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        app_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
    finally:
        app_state.is_processing = False
        mp.update()

@mp.page(path="/")
def chat_page():
    """Main chat interface page."""
    mp.title("Agentic Kernel Chat")
    
    # Initialize agent on first load
    if app_state.agent is None:
        app_state.initialize_agent()
    
    # Display chat messages
    with container(style={"padding": "20px", "maxWidth": "800px", "margin": "0 auto"}):
        # Welcome message
        with container(style={"marginBottom": "20px"}):
            markdown("# Agentic Kernel Chat")
            markdown("Welcome to the Agentic Kernel chat interface powered by Gemini.")
        
        # Chat history
        with container(style={"height": "400px", "overflowY": "auto", "border": "1px solid #ddd", "padding": "10px", "marginBottom": "20px"}):
            if not app_state.messages:
                markdown("*Start a conversation by typing a message below.*")
            else:
                for msg in app_state.messages:
                    role = msg["role"]
                    content = msg["content"]
                    
                    if role == "user":
                        with container(style={"textAlign": "right", "marginBottom": "10px"}):
                            markdown(f"**You**: {content}")
                    elif role == "assistant":
                        with container(style={"textAlign": "left", "marginBottom": "10px"}):
                            markdown(f"**Assistant**: {content}")
                    elif role == "system":
                        with container(style={"textAlign": "center", "marginBottom": "10px", "color": "#888"}):
                            markdown(f"*{content}*")
        
        # Input area
        with container(style={"display": "flex", "gap": "10px"}):
            user_input = text_input(
                placeholder="Type your message here...",
                disabled=app_state.is_processing,
                style={"flexGrow": 1}
            )
            
            def on_send():
                message = user_input.value
                if message:
                    user_input.value = ""  # Clear input
                    mp.update()
                    mp.spawn(handle_send_message(message))
            
            button(
                "Send", 
                on_click=on_send,
                disabled=app_state.is_processing,
                style={"padding": "10px 20px"}
            )

# --- Main Execution ---
if __name__ == "__main__":
    # Start Mesop server
    mp.run()
