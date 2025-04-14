"""Utility functions for integrating ADK and A2A in the chat system."""

import asyncio
import logging
import os
from typing import Any

from dotenv import load_dotenv
from google.adk.agents import Agent as ADKAgent
from google.adk.tools import FunctionTool

from agentic_kernel.communication.a2a.client import A2AClient
from agentic_kernel.communication.a2a.server import A2AServer
from agentic_kernel.communication.a2a.types import AgentCapability, AgentCard, Skill

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class ADKA2AAgent:
    """A wrapper class that integrates ADK Agent with A2A capabilities."""

    def __init__(
        self,
        name: str,
        description: str,
        model: str = "gemini-2.0-flash-exp",
        host: str = "localhost",
        port: int = None,
    ):
        """Initialize the ADKA2AAgent.

        Args:
            name: The name of the agent
            description: A description of the agent
            model: The model to use for the agent
            host: The host for the A2A server
            port: The port for the A2A server (if None, a random port will be assigned)
        """
        self.name = name
        self.description = description
        self.model = model
        self.host = host
        self.port = port or self._get_random_port()

        # Initialize ADK Agent
        self.adk_agent = ADKAgent(name=name, model=model)

        # Initialize A2A components
        self.agent_card = self._create_agent_card()
        self.a2a_server = A2AServer(
            agent_card=self.agent_card,
            host=host,
            port=self.port,
        )

        # Dictionary to store A2A clients for other agents
        self.a2a_clients = {}

        # Store function tools
        self.tools = []

    def _get_random_port(self) -> int:
        """Get a random available port.

        Returns:
            A random available port
        """
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", 0))
            return s.getsockname()[1]

    def _create_agent_card(self) -> AgentCard:
        """Create an A2A agent card for this agent.

        Returns:
            An A2A agent card
        """
        return AgentCard(
            name=self.name,
            description=self.description,
            capabilities=[],
            provider={"name": "Agentic-Kernel", "description": "ADK A2A Chat System"},
        )

    def add_tool(self, tool: FunctionTool) -> None:
        """Add a tool to the agent.

        Args:
            tool: The tool to add
        """
        # Add to ADK agent
        self.adk_agent.add_tool(tool)

        # Store for A2A capability registration
        self.tools.append(tool)

        # Register as A2A capability
        capability = AgentCapability(
            name=tool.name,
            description=tool.description,
            skills=[
                Skill(
                    name=tool.name,
                    description=tool.description,
                ),
            ],
        )
        self.agent_card.capabilities.append(capability)

    def register_a2a_method(
        self, method_name: str, handler, streaming: bool = False
    ) -> None:
        """Register an A2A method with the server.

        Args:
            method_name: The name of the method
            handler: The handler function
            streaming: Whether the method is streaming
        """
        self.a2a_server.registry.register(method_name, handler, streaming)

    def connect_to_agent(self, agent_name: str, base_url: str) -> None:
        """Connect to another agent via A2A.

        Args:
            agent_name: The name of the agent to connect to
            base_url: The base URL of the agent's A2A server
        """
        self.a2a_clients[agent_name] = A2AClient(base_url=base_url)
        logger.info(f"Connected to agent {agent_name} at {base_url}")

    async def start(self) -> None:
        """Start the A2A server."""
        logger.info(f"ADKA2AAgent [{self.name}]: Starting service (super().start)...")
        await super().start()
        logger.info(
            f"ADKA2AAgent [{self.name}]: Service started (super().start completed)."
        )

        # Start the server in a separate task
        asyncio.create_task(self._run_server())
        logger.info(f"Agent {self.name} started on {self.host}:{self.port}")

    async def _run_server(self) -> None:
        """Run the A2A server."""
        await self.a2a_server.run()

    async def send_task(
        self,
        recipient_agent: str,
        task_description: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a task to another agent via A2A.

        Args:
            recipient_agent: The name of the recipient agent
            task_description: A description of the task
            params: Parameters for the task

        Returns:
            The task result
        """
        if recipient_agent not in self.a2a_clients:
            raise ValueError(f"No connection to agent {recipient_agent}")

        client = self.a2a_clients[recipient_agent]

        # Create task parameters
        task_params = {
            "description": task_description,
            "input": params,
        }

        # Send the task
        response = await client.tasks_send(task_params)

        return response


def setup_adk_a2a_environment() -> None:
    """Set up the environment for the ADK A2A Chat System."""
    # Ensure required environment variables are set
    required_vars = ["OPENAI_API_KEY", "GOOGLE_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.warning("Some functionality may not work correctly.")
