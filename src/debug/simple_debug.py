"""Simple Chainlit app for debugging."""

import os
import logging
import uuid
import sys
from typing import Dict, Any, List
from dotenv import load_dotenv
import chainlit as cl
from agentic_kernel.plugins.base import BasePlugin
from agentic_kernel.orchestrator.core import OrchestratorAgent
from agentic_kernel.config.loader import ConfigLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_imports():
    """Test critical imports."""
    print("Testing imports...")
    try:
        from agentic_kernel.config.loader import ConfigLoader
        print("✅ ConfigLoader imported successfully")

        from agentic_kernel.config import AgentConfig
        print("✅ AgentConfig imported successfully")

        from agentic_kernel.agents.base import BaseAgent
        print("✅ BaseAgent imported successfully")

        from agentic_kernel.types import Task, WorkflowStep
        print("✅ Task and WorkflowStep imported successfully")

        from agentic_kernel.ledgers import TaskLedger, ProgressLedger
        print("✅ TaskLedger and ProgressLedger imported successfully")

        from agentic_kernel.orchestrator.core import OrchestratorAgent
        print("✅ OrchestratorAgent imported successfully")

        # Test initialization
        print("\nTesting component initialization...")
        config_loader = ConfigLoader()
        print("✅ ConfigLoader initialized successfully")

        task_ledger = TaskLedger(goal="Test goal")
        print("✅ TaskLedger initialized successfully")

        progress_ledger = ProgressLedger(task_id=str(uuid.uuid4()))
        print("✅ ProgressLedger initialized successfully")

        return True
    except Exception as e:
        print(f"❌ Error during import testing: {e}")
        logger.error(f"Import testing failed: {e}", exc_info=True)
        return False

@cl.on_chat_start
async def start_chat():
    """Initialize the chat session."""
    try:
        # Import and initialize the core components
        from agentic_kernel.config.loader import ConfigLoader
        from agentic_kernel.ledgers import TaskLedger, ProgressLedger

        config_loader = ConfigLoader()
        task_ledger = TaskLedger(goal="Assist users with their requests")
        progress_ledger = ProgressLedger(task_id=str(uuid.uuid4()))

        # Store in the user session
        cl.user_session.set("task_ledger", task_ledger)
        cl.user_session.set("progress_ledger", progress_ledger)

        # Welcome message
        await cl.Message(
            content=(
                "👋 Hello! I'm a simple debug version of the Agentic Kernel architecture.\n\n"
                "This is a minimal app for testing core functionality."
            )
        ).send()

    except Exception as e:
        error_msg = f"Failed to initialize debug session: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await cl.Message(content=error_msg).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages."""
    msg = cl.Message(content="")

    try:
        # Echo the message back
        await msg.stream_token(f"You said: {message.content}\n\n")
        await msg.stream_token("Debug session is functioning correctly!")
        await msg.send()
    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await cl.Message(content=f"⚠️ {error_msg}").send()

if __name__ == "__main__":
    # Run import test first
    if not test_imports():
        sys.exit(1)

    print("\nAll tests passed! Starting Chainlit app...\n")
    print("Run with: chainlit run src/simple_debug.py -w\n")

    # For direct debugging, uncomment this:
    # from chainlit.cli import run_chainlit
    # run_chainlit(__file__) 

# Configuration Loading
# Ensure you have a valid config.json or provide the path
config_path = "path/to/your/config.json"  # Replace with your config path if needed
# loader = ConfigLoader()
# config = loader.load_config()


# Agent Classes (Assuming they are defined elsewhere)
from agentic_kernel.agents import BaseAgent, ChatAgent, WebSurferAgent, FileSurferAgent
from agentic_kernel.config_types import AgentConfig, LLMMapping

# Task and Ledger Classes
from agentic_kernel.types import Task, WorkflowStep
from agentic_kernel.ledgers import TaskLedger, ProgressLedger

# Dummy Plugin for testing
class DummyPlugin(BasePlugin):
    """A dummy plugin for testing purposes."""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        print(f"DummyPlugin executed with args: {kwargs}")
        return {"result": "Dummy plugin result"}

@cl.on_chat_start
async def main():
    """Main function to run the debug workflow."""
    print("Starting debug workflow...")
    # Example Usage
    # Create necessary configurations and instances
    llm_mapping = LLMMapping(model="gpt-4", endpoint="azure_openai")
    chat_agent_config = AgentConfig(
        name="ChatAgent",
        type="ChatAgent",
        description="Handles chat interactions",
        llm_mapping=llm_mapping,
    )
    # Create agents, tasks, ledgers, etc. as needed for your debug scenario
    # ...
    print("Debug workflow setup complete.")

async def run_debug_workflow():
    """Runs the actual debug logic (placeholder)."""
    # Replace with your actual debug workflow logic
    print("Executing debug workflow...")
    await asyncio.sleep(2) # Simulate work
    print("Debug workflow finished.")

if __name__ == "__main__":
    # This part might not run correctly with Chainlit's execution model.
    # Use Chainlit's decorator pattern for UI integration.
    # asyncio.run(main()) # This likely won't work as expected with cl.on_chat_start
    # Consider running specific debug functions directly if needed without UI
    # asyncio.run(run_debug_workflow())

    # If you need to run chainlit from script (less common):
    try:
        from chainlit.cli import run_chainlit
        # This might require specific setup or context
        # run_chainlit(__file__) 
        pass # Placeholder to avoid syntax error
    except ImportError:
        print("Chainlit CLI not found. Run with 'chainlit run simple_debug.py -w'") 
