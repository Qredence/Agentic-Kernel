"""Mesop UI for the ADK A2A Chat System."""

import asyncio
import logging
from typing import Any

import httpx
import mesop as mp
from mesop import component

from ..utils.adk_a2a_utils import setup_adk_a2a_environment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
conversation_history = []
agents_info = {}
server_url = "http://localhost:8080"
http_client = None
is_processing = False


@component
def chat_header():
    """Render the chat header."""
    mp.heading("ADK A2A Chat System", level=1)
    mp.text(
        "This chat system uses Google's Agent Development Kit (ADK) and Agent-to-Agent (A2A) "
        "communication protocol for multi-agent orchestration.",
    )
    mp.divider()


@component
def agent_info_panel():
    """Render the agent information panel."""
    if not agents_info:
        mp.text("Loading agent information...")
        return

    mp.heading("Available Agents", level=2)
    
    for agent_name, agent_data in agents_info.items():
        with mp.card():
            mp.heading(agent_name.capitalize(), level=3)
            mp.text(agent_data.get("description", "No description available"))
            mp.text(f"Model: {agent_data.get('model', 'Unknown')}")


@component
def chat_message(message: dict[str, Any]):
    """Render a chat message.
    
    Args:
        message: The message to render
    """
    is_user = message.get("role") == "user"
    content = message.get("content", "")
    
    with mp.card(elevation=1):
        mp.heading(
            "You" if is_user else "Agent", 
            level=4,
            color="primary" if is_user else "secondary",
        )
        mp.markdown(content)
        
        if not is_user and "activity_id" in message:
            mp.text(f"Activity ID: {message['activity_id']}", size="small", color="hint")


@component
def chat_history():
    """Render the chat history."""
    if not conversation_history:
        mp.text("No messages yet. Start the conversation by typing a message below.")
        return
    
    for message in conversation_history:
        chat_message(message)


@component
def message_input():
    """Render the message input."""
    global is_processing
    
    message = mp.state("")
    
    def on_change(value):
        message.value = value
    
    def on_submit():
        if not message.value or is_processing:
            return
        
        # Add user message to conversation
        user_message = {"role": "user", "content": message.value}
        conversation_history.append(user_message)
        
        # Clear input
        temp = message.value
        message.value = ""
        
        # Send message to server
        asyncio.create_task(send_message(temp))
    
    mp.text_field(
        label="Type your message",
        on_change=on_change,
        value=message.value,
        disabled=is_processing,
    )
    
    mp.button(
        "Send",
        on_click=on_submit,
        disabled=not message.value or is_processing,
        variant="filled",
    )
    
    if is_processing:
        mp.progress_circular(indeterminate=True)


async def initialize_client():
    """Initialize the HTTP client and fetch agent information."""
    global http_client, agents_info
    
    # Create HTTP client
    http_client = httpx.AsyncClient()
    
    # Check if server is running
    try:
        response = await http_client.get(f"{server_url}/")
        data = response.json()
        if data.get("status") != "ok":
            logger.error("Server is not running properly")
            return False
    except Exception as e:
        logger.error(f"Error connecting to server: {str(e)}")
        return False
    
    # Get agent information
    try:
        response = await http_client.get(f"{server_url}/agents")
        data = response.json()
        agents_info = data.get("agents", {})
    except Exception as e:
        logger.error(f"Error getting agent information: {str(e)}")
    
    return True


async def send_message(message: str):
    """Send a message to the server.
    
    Args:
        message: The message to send
    """
    global is_processing, http_client
    
    if not http_client:
        logger.error("HTTP client not initialized")
        return
    
    is_processing = True
    
    try:
        response = await http_client.post(
            f"{server_url}/chat",
            json={"message": message},
            timeout=60.0,  # Longer timeout for agent processing
        )
        data = response.json()
        
        if data.get("status") == "ok":
            # Add agent response to conversation
            agent_message = {
                "role": "agent",
                "content": data.get("response", ""),
                "activity_id": data.get("activity_id", ""),
            }
            conversation_history.append(agent_message)
        else:
            # Add error message to conversation
            error_message = {
                "role": "agent",
                "content": f"Error: {data.get('message', 'Unknown error')}",
            }
            conversation_history.append(error_message)
    
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        # Add error message to conversation
        error_message = {
            "role": "agent",
            "content": f"Error: {str(e)}",
        }
        conversation_history.append(error_message)
    
    finally:
        is_processing = False


@mp.main
async def main():
    """Main entry point for the Mesop UI."""
    # Set up environment
    setup_adk_a2a_environment()
    
    # Initialize client
    server_running = await initialize_client()
    if not server_running:
        mp.heading("Error", level=2, color="error")
        mp.text("Could not connect to the chat server. Please make sure it's running.")
        return
    
    # Render UI
    with mp.flex(direction="column", gap=2):
        chat_header()
        
        with mp.flex(direction="row", gap=2):
            # Left panel - Agent information
            with mp.flex(direction="column", gap=2, style={"width": "30%"}):
                agent_info_panel()
            
            # Right panel - Chat interface
            with mp.flex(direction="column", gap=2, style={"width": "70%"}):
                with mp.card(elevation=2, style={"height": "70vh", "overflow": "auto"}):
                    chat_history()
                
                message_input()


async def cleanup():
    """Clean up resources."""
    global http_client
    
    if http_client:
        await http_client.aclose()


def run_mesop_ui():
    """Run the Mesop UI."""
    try:
        mp.run()
    finally:
        asyncio.run(cleanup())


if __name__ == "__main__":
    run_mesop_ui()