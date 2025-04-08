"""Agent system implementation for managing agent lifecycle and communication.

This module implements the core agent system that manages:
1. Agent lifecycle (creation, registration, destruction)
2. Inter-agent communication
3. System-wide configuration
4. Resource management
5. Error handling and recovery
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type
from uuid import uuid4

from ..agents.base import BaseAgent
from ..agents.chat_agent import ChatAgent
from ..agents.terminal_agent import TerminalAgent
from ..communication.message import Message, MessagePriority, MessageType
from ..communication.protocol import MessageBus
from ..config import AgentConfig, SystemConfig
from ..exceptions import AgentError, SystemError
from ..orchestrator import OrchestratorAgent

logger = logging.getLogger(__name__)


class AgentSystem:
    """Core system for managing agents and their interactions.

    The AgentSystem is responsible for:
    1. Managing agent lifecycle
    2. Facilitating inter-agent communication
    3. Handling system-wide configuration
    4. Managing system resources
    5. Error handling and recovery

    Attributes:
        config (SystemConfig): System-wide configuration
        message_bus (MessageBus): Central message bus for agent communication
        orchestrator (OrchestratorAgent): System orchestrator
        agents (Dict[str, BaseAgent]): Registered agents by ID
    """

    def __init__(self, config: SystemConfig):
        """Initialize the agent system.

        Args:
            config: System-wide configuration
        """
        self.config = config
        self.message_bus = MessageBus()
        self.agents: Dict[str, BaseAgent] = {}

        # Initialize orchestrator
        orchestrator_config = AgentConfig(
            name="orchestrator", description="System orchestrator agent", parameters={}
        )
        self.orchestrator = OrchestratorAgent(orchestrator_config, self.message_bus)

        # Start message bus
        asyncio.create_task(self.message_bus.start())

    async def create_agent(
        self, agent_type: str, config: Optional[AgentConfig] = None
    ) -> BaseAgent:
        """Create a new agent instance.

        Args:
            agent_type: Type of agent to create
            config: Optional agent configuration

        Returns:
            The created agent instance

        Raises:
            AgentError: If agent type is unknown or creation fails
        """
        if not config:
            config = AgentConfig(
                name=f"{agent_type}_{uuid4().hex[:8]}",
                description=f"{agent_type} agent",
                parameters={},
            )

        try:
            # Create agent instance
            agent: BaseAgent
            if agent_type == "chat":
                agent = ChatAgent(config, self.message_bus)
            elif agent_type == "terminal":
                agent = TerminalAgent(config, self.message_bus)
            else:
                raise AgentError(f"Unknown agent type: {agent_type}")

            # Register with orchestrator
            self.orchestrator.register_agent(agent)

            # Store in system
            self.agents[agent.agent_id] = agent

            return agent

        except Exception as e:
            raise AgentError(f"Failed to create agent: {str(e)}")

    async def destroy_agent(self, agent_id: str) -> None:
        """Destroy an agent instance.

        Args:
            agent_id: ID of the agent to destroy

        Raises:
            AgentError: If agent not found or destruction fails
        """
        if agent_id not in self.agents:
            raise AgentError(f"Agent not found: {agent_id}")

        try:
            agent = self.agents[agent_id]

            # Unsubscribe from message bus
            if agent.protocol:
                await agent.protocol.stop()

            # Remove from system
            del self.agents[agent_id]

        except Exception as e:
            raise AgentError(f"Failed to destroy agent: {str(e)}")

    async def broadcast_message(
        self,
        message_type: MessageType,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> None:
        """Broadcast a message to all agents.

        Args:
            message_type: Type of message to broadcast
            content: Message content
            priority: Message priority

        Raises:
            SystemError: If broadcast fails
        """
        try:
            # Create base message
            message = Message(
                message_type=message_type,
                content=content,
                priority=priority,
                sender="system",
            )

            # Send to all agents
            for agent in self.agents.values():
                if agent.protocol:
                    await agent.protocol.handle_message(message)

        except Exception as e:
            raise SystemError(f"Failed to broadcast message: {str(e)}")

    async def stop(self) -> None:
        """Stop the agent system.

        This method:
        1. Stops all agents
        2. Stops the message bus
        3. Cleans up resources

        Raises:
            SystemError: If shutdown fails
        """
        try:
            # Stop all agents
            for agent_id in list(self.agents.keys()):
                await self.destroy_agent(agent_id)

            # Stop message bus
            await self.message_bus.stop()

        except Exception as e:
            raise SystemError(f"Failed to stop system: {str(e)}")

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID.

        Args:
            agent_id: ID of the agent to get

        Returns:
            The agent instance if found, None otherwise
        """
        return self.agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """Get information about all registered agents.

        Returns:
            List of agent information dictionaries
        """
        return [
            {
                "id": agent.agent_id,
                "type": agent.type,
                "name": agent.config.name,
                "description": agent.config.description,
            }
            for agent in self.agents.values()
        ]

    async def get_agent_capabilities(self, agent_id: str) -> Dict[str, Any]:
        """Get the capabilities of an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Dictionary of agent capabilities

        Raises:
            AgentError: If agent not found
        """
        agent = self.get_agent(agent_id)
        if not agent:
            raise AgentError(f"Agent not found: {agent_id}")

        return agent._get_supported_tasks()

    async def get_system_status(self) -> Dict[str, Any]:
        """Get the current status of the system.

        Returns:
            Dictionary containing system status information
        """
        return {
            "agent_count": len(self.agents),
            "agents": self.list_agents(),
            "message_bus_active": self.message_bus.is_running(),
            "config": self.config.dict(),
        }
