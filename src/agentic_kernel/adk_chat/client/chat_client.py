"""Chat Client for the ADK A2A Chat System."""

import asyncio
import logging
import sys
from typing import Any

import httpx
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rich console for pretty output
console = Console()


class ChatClient:
    """Chat Client that provides a user interface for interacting with the chat system."""

    def __init__(
        self,
        server_url: str = "http://localhost:8080",
    ):
        """Initialize the ChatClient.

        Args:
            server_url: The URL of the chat server
        """
        self.server_url = server_url
        self.http_client = httpx.AsyncClient()
        self.session = PromptSession()
        self.conversation_history = []

    async def check_server(self) -> bool:
        """Check if the server is running.

        Returns:
            True if the server is running, False otherwise
        """
        try:
            response = await self.http_client.get(f"{self.server_url}/")
            data = response.json()
            return data.get("status") == "ok"
        except Exception as e:
            logger.error(f"Error checking server: {str(e)}")
            return False

    async def get_agents(self) -> dict[str, dict[str, Any]]:
        """Get information about the available agents.

        Returns:
            A dictionary of agent information
        """
        try:
            response = await self.http_client.get(f"{self.server_url}/agents")
            data = response.json()
            return data.get("agents", {})
        except Exception as e:
            logger.error(f"Error getting agents: {str(e)}")
            return {}

    async def send_message(self, message: str) -> dict[str, Any]:
        """Send a message to the chat server.

        Args:
            message: The message to send

        Returns:
            The server response
        """
        try:
            response = await self.http_client.post(
                f"{self.server_url}/chat",
                json={"message": message},
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return {
                "status": "error",
                "message": f"Error sending message: {str(e)}",
            }

    def display_welcome(self) -> None:
        """Display a welcome message."""
        console.print(
            Panel.fit(
                "[bold blue]Welcome to the ADK A2A Chat System![/bold blue]\n\n"
                "This chat system uses Google's Agent Development Kit (ADK) and Agent-to-Agent (A2A) "
                "communication protocol for multi-agent orchestration.\n\n"
                "Type your messages and press Enter to chat with the agents.\n"
                "Type [bold]'exit'[/bold] or [bold]'quit'[/bold] to end the session.",
                title="ADK A2A Chat",
                border_style="blue",
            ),
        )

    async def display_agents(self) -> None:
        """Display information about the available agents."""
        agents = await self.get_agents()

        if not agents:
            console.print("[bold red]No agents available[/bold red]")
            return

        console.print(
            Panel.fit(
                "\n".join(
                    [
                        f"[bold]{name}[/bold]: {info['description']}"
                        for name, info in agents.items()
                    ]
                ),
                title="Available Agents",
                border_style="green",
            ),
        )

    def display_user_message(self, message: str) -> None:
        """Display a user message.

        Args:
            message: The user message
        """
        console.print(
            Panel.fit(
                message,
                title="You",
                border_style="blue",
            ),
        )

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})

    def display_agent_response(self, response: dict[str, Any]) -> None:
        """Display an agent response.

        Args:
            response: The agent response
        """
        if response.get("status") == "ok":
            # Format the response as markdown
            md = Markdown(response.get("response", ""))

            console.print(
                Panel.fit(
                    md,
                    title="Agent",
                    border_style="green",
                ),
            )

            # Add to conversation history
            self.conversation_history.append(
                {
                    "role": "agent",
                    "content": response.get("response", ""),
                    "activity_id": response.get("activity_id", ""),
                }
            )
        else:
            # Display error
            console.print(
                Panel.fit(
                    response.get("message", "Unknown error"),
                    title="Error",
                    border_style="red",
                ),
            )

    async def run(self) -> None:
        """Run the chat client."""
        # Check if server is running
        if not await self.check_server():
            console.print(
                "[bold red]Error: Could not connect to the chat server[/bold red]"
            )
            return

        # Display welcome message
        self.display_welcome()

        # Display available agents
        await self.display_agents()

        # Main chat loop
        with patch_stdout():
            while True:
                # Get user input
                message = await self.session.prompt_async("\n[You]: ")

                # Check for exit command
                if message.lower() in ["exit", "quit"]:
                    console.print("[bold blue]Goodbye![/bold blue]")
                    break

                # Display user message
                self.display_user_message(message)

                # Send message to server
                response = await self.send_message(message)

                # Display agent response
                self.display_agent_response(response)

    async def close(self) -> None:
        """Close the chat client."""
        await self.http_client.aclose()


async def create_and_run_client(
    server_url: str = "http://localhost:8080",
) -> None:
    """Create and run the chat client.

    Args:
        server_url: The URL of the chat server
    """
    client = ChatClient(server_url=server_url)
    try:
        await client.run()
    finally:
        await client.close()


if __name__ == "__main__":
    # Get server URL from command line arguments
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"

    # Run the client
    asyncio.run(create_and_run_client(server_url=server_url))
