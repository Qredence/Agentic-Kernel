"""Agent capability advertisement and discovery mechanisms.

This module implements a registry for agent capabilities, allowing agents to
advertise their capabilities and discover the capabilities of other agents
in the system.

Key features:
1. Agent capability registration
2. Capability discovery and querying
3. Agent registry for tracking available agents
4. Capability matching and filtering
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .message import (
    AgentDiscoveryMessage,
    CapabilityRequestMessage,
    CapabilityResponseMessage,
    Message,
    MessageType,
)
from .protocol import CommunicationProtocol

logger = logging.getLogger(__name__)


class AgentCapability:
    """Representation of an agent capability.

    This class represents a specific capability that an agent can provide,
    including metadata about the capability's performance and limitations.

    Attributes:
        capability_id: Unique identifier for the capability
        name: Name of the capability
        description: Description of what the capability does
        capability_type: Type of capability (reasoning, planning, etc.)
        parameters: Parameters that can be provided when using the capability
        performance_metrics: Metrics about the capability's performance
        limitations: Known limitations of the capability
        version: Version of the capability implementation
        last_updated: When the capability was last updated
    """

    def __init__(
        self,
        name: str,
        description: str,
        capability_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
        limitations: Optional[Dict[str, Any]] = None,
        version: str = "1.0.0",
    ):
        """Initialize a capability.

        Args:
            name: Name of the capability
            description: Description of what the capability does
            capability_type: Type of capability (reasoning, planning, etc.)
            parameters: Parameters that can be provided when using the capability
            performance_metrics: Metrics about the capability's performance
            limitations: Known limitations of the capability
            version: Version of the capability implementation
        """
        self.capability_id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.capability_type = capability_type
        self.parameters = parameters or {}
        self.performance_metrics = performance_metrics or {}
        self.limitations = limitations or {}
        self.version = version
        self.last_updated = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the capability to a dictionary.

        Returns:
            Dictionary representation of the capability
        """
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "capability_type": self.capability_type,
            "parameters": self.parameters,
            "performance_metrics": self.performance_metrics,
            "limitations": self.limitations,
            "version": self.version,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCapability":
        """Create a capability from a dictionary.

        Args:
            data: Dictionary representation of the capability

        Returns:
            AgentCapability instance
        """
        capability = cls(
            name=data["name"],
            description=data["description"],
            capability_type=data["capability_type"],
            parameters=data.get("parameters", {}),
            performance_metrics=data.get("performance_metrics", {}),
            limitations=data.get("limitations", {}),
            version=data.get("version", "1.0.0"),
        )
        capability.capability_id = data["capability_id"]
        capability.last_updated = datetime.fromisoformat(data["last_updated"])
        return capability


class AgentInfo:
    """Information about an agent in the system.

    This class stores information about an agent, including its
    capabilities, status, and metadata.

    Attributes:
        agent_id: Unique identifier for the agent
        agent_type: Type/role of the agent
        capabilities: List of agent capabilities
        status: Current operational status
        resources: Available resources and constraints
        metadata: Additional agent-specific information
        last_seen: When the agent was last active
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: Optional[List[AgentCapability]] = None,
        status: str = "active",
        resources: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize agent information.

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type/role of the agent
            capabilities: List of agent capabilities
            status: Current operational status
            resources: Available resources and constraints
            metadata: Additional agent-specific information
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.capabilities = capabilities or []
        self.status = status
        self.resources = resources or {}
        self.metadata = metadata or {}
        self.last_seen = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the agent info to a dictionary.

        Returns:
            Dictionary representation of the agent info
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": [cap.to_dict() for cap in self.capabilities],
            "status": self.status,
            "resources": self.resources,
            "metadata": self.metadata,
            "last_seen": self.last_seen.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInfo":
        """Create agent info from a dictionary.

        Args:
            data: Dictionary representation of the agent info

        Returns:
            AgentInfo instance
        """
        capabilities = [
            AgentCapability.from_dict(cap_data) for cap_data in data.get("capabilities", [])
        ]
        agent_info = cls(
            agent_id=data["agent_id"],
            agent_type=data["agent_type"],
            capabilities=capabilities,
            status=data.get("status", "active"),
            resources=data.get("resources", {}),
            metadata=data.get("metadata", {}),
        )
        agent_info.last_seen = datetime.fromisoformat(data["last_seen"])
        return agent_info

    def update_last_seen(self):
        """Update the last_seen timestamp to the current time."""
        self.last_seen = datetime.utcnow()

    def add_capability(self, capability: AgentCapability):
        """Add a capability to the agent.

        Args:
            capability: Capability to add
        """
        # Check if capability with same ID already exists
        for i, existing_cap in enumerate(self.capabilities):
            if existing_cap.capability_id == capability.capability_id:
                # Replace the existing capability
                self.capabilities[i] = capability
                return

        # Add new capability
        self.capabilities.append(capability)

    def remove_capability(self, capability_id: str) -> bool:
        """Remove a capability from the agent.

        Args:
            capability_id: ID of the capability to remove

        Returns:
            True if the capability was removed, False if not found
        """
        for i, cap in enumerate(self.capabilities):
            if cap.capability_id == capability_id:
                self.capabilities.pop(i)
                return True
        return False

    def get_capability_by_id(self, capability_id: str) -> Optional[AgentCapability]:
        """Get a capability by its ID.

        Args:
            capability_id: ID of the capability to get

        Returns:
            The capability if found, None otherwise
        """
        for cap in self.capabilities:
            if cap.capability_id == capability_id:
                return cap
        return None

    def get_capabilities_by_type(self, capability_type: str) -> List[AgentCapability]:
        """Get all capabilities of a specific type.

        Args:
            capability_type: Type of capabilities to get

        Returns:
            List of capabilities of the specified type
        """
        return [cap for cap in self.capabilities if cap.capability_type == capability_type]


class CapabilityRegistry:
    """Registry for agent capabilities and discovery.

    This class provides a central registry for agents to advertise their
    capabilities and for other agents to discover available capabilities
    in the system.

    Attributes:
        agents: Dictionary mapping agent IDs to their information
        protocol: Communication protocol for sending messages
    """

    def __init__(self, protocol: Optional[CommunicationProtocol] = None):
        """Initialize the capability registry.

        Args:
            protocol: Optional communication protocol for sending messages
        """
        self.agents: Dict[str, AgentInfo] = {}
        self.protocol = protocol
        self._lock = asyncio.Lock()

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: Optional[List[AgentCapability]] = None,
        status: str = "active",
        resources: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentInfo:
        """Register an agent with the registry.

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type/role of the agent
            capabilities: List of agent capabilities
            status: Current operational status
            resources: Available resources and constraints
            metadata: Additional agent-specific information

        Returns:
            The registered agent info
        """
        async with self._lock:
            agent_info = AgentInfo(
                agent_id=agent_id,
                agent_type=agent_type,
                capabilities=capabilities,
                status=status,
                resources=resources,
                metadata=metadata,
            )
            self.agents[agent_id] = agent_info
            logger.info(f"Agent {agent_id} registered with {len(capabilities or [])} capabilities")
            return agent_info

    async def update_agent(
        self,
        agent_id: str,
        status: Optional[str] = None,
        resources: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentInfo]:
        """Update an agent's information.

        Args:
            agent_id: ID of the agent to update
            status: New status (if provided)
            resources: New resources (if provided)
            metadata: New metadata (if provided)

        Returns:
            The updated agent info, or None if the agent is not registered
        """
        async with self._lock:
            if agent_id not in self.agents:
                logger.warning(f"Attempted to update unregistered agent {agent_id}")
                return None

            agent_info = self.agents[agent_id]
            agent_info.update_last_seen()

            if status is not None:
                agent_info.status = status
            if resources is not None:
                agent_info.resources = resources
            if metadata is not None:
                agent_info.metadata = metadata

            logger.debug(f"Agent {agent_id} information updated")
            return agent_info

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the registry.

        Args:
            agent_id: ID of the agent to unregister

        Returns:
            True if the agent was unregistered, False if not found
        """
        async with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                logger.info(f"Agent {agent_id} unregistered")
                return True
            return False

    async def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Get information about an agent.

        Args:
            agent_id: ID of the agent to get information for

        Returns:
            The agent info if found, None otherwise
        """
        async with self._lock:
            return self.agents.get(agent_id)

    async def add_agent_capability(
        self, agent_id: str, capability: AgentCapability
    ) -> Optional[AgentInfo]:
        """Add a capability to an agent.

        Args:
            agent_id: ID of the agent to add the capability to
            capability: Capability to add

        Returns:
            The updated agent info, or None if the agent is not registered
        """
        async with self._lock:
            if agent_id not in self.agents:
                logger.warning(f"Attempted to add capability to unregistered agent {agent_id}")
                return None

            agent_info = self.agents[agent_id]
            agent_info.add_capability(capability)
            agent_info.update_last_seen()
            logger.debug(f"Added capability {capability.name} to agent {agent_id}")
            return agent_info

    async def remove_agent_capability(
        self, agent_id: str, capability_id: str
    ) -> Optional[AgentInfo]:
        """Remove a capability from an agent.

        Args:
            agent_id: ID of the agent to remove the capability from
            capability_id: ID of the capability to remove

        Returns:
            The updated agent info, or None if the agent is not registered
        """
        async with self._lock:
            if agent_id not in self.agents:
                logger.warning(f"Attempted to remove capability from unregistered agent {agent_id}")
                return None

            agent_info = self.agents[agent_id]
            if agent_info.remove_capability(capability_id):
                logger.debug(f"Removed capability {capability_id} from agent {agent_id}")
            else:
                logger.warning(
                    f"Capability {capability_id} not found for agent {agent_id}"
                )
            agent_info.update_last_seen()
            return agent_info

    async def get_agents_by_capability_type(self, capability_type: str) -> List[AgentInfo]:
        """Get all agents that have a specific capability type.

        Args:
            capability_type: Type of capability to search for

        Returns:
            List of agents with the specified capability type
        """
        async with self._lock:
            return [
                agent
                for agent in self.agents.values()
                if any(cap.capability_type == capability_type for cap in agent.capabilities)
            ]

    async def get_agents_by_status(self, status: str) -> List[AgentInfo]:
        """Get all agents with a specific status.

        Args:
            status: Status to search for

        Returns:
            List of agents with the specified status
        """
        async with self._lock:
            return [agent for agent in self.agents.values() if agent.status == status]

    async def get_all_agents(self) -> List[AgentInfo]:
        """Get all registered agents.

        Returns:
            List of all registered agents
        """
        async with self._lock:
            return list(self.agents.values())

    async def handle_agent_discovery_message(self, message: AgentDiscoveryMessage) -> None:
        """Handle an agent discovery message.

        This method processes an agent discovery message, registering or
        updating the agent's information in the registry.

        Args:
            message: The agent discovery message to process
        """
        content = message.content
        agent_id = content.get("agent_id")
        agent_type = content.get("agent_type")
        capabilities_data = content.get("capabilities", [])
        status = content.get("status", "active")
        resources = content.get("resources", {})
        metadata = content.get("metadata", {})

        # Convert capability strings to AgentCapability objects
        capabilities = []
        for cap_name in capabilities_data:
            # Create a basic capability with minimal information
            capability = AgentCapability(
                name=cap_name,
                description=f"Capability: {cap_name}",
                capability_type=cap_name,
            )
            capabilities.append(capability)

        # Register or update the agent
        if agent_id in self.agents:
            await self.update_agent(
                agent_id=agent_id,
                status=status,
                resources=resources,
                metadata=metadata,
            )
            # Update capabilities
            agent_info = self.agents[agent_id]
            for capability in capabilities:
                agent_info.add_capability(capability)
        else:
            await self.register_agent(
                agent_id=agent_id,
                agent_type=agent_type,
                capabilities=capabilities,
                status=status,
                resources=resources,
                metadata=metadata,
            )

        logger.info(f"Processed agent discovery message from {agent_id}")

    async def handle_capability_request_message(
        self, message: CapabilityRequestMessage
    ) -> Optional[str]:
        """Handle a capability request message.

        This method processes a capability request message, sending a
        response with the requested capability information.

        Args:
            message: The capability request message to process

        Returns:
            The message ID of the response, or None if no response was sent
        """
        if not self.protocol:
            logger.error("Cannot handle capability request: no protocol available")
            return None

        content = message.content
        capability_types = content.get("capability_types")
        detail_level = content.get("detail_level", "basic")

        # Get the agent info for the requesting agent
        agent_id = message.sender
        agent_info = await self.get_agent_info(agent_id)

        if not agent_info:
            logger.warning(f"Capability request from unknown agent {agent_id}")
            # We can still respond with capabilities from other agents

        # Collect capabilities to return
        capabilities = []
        performance_metrics = {}
        limitations = {}

        # If specific capability types were requested, filter by those
        if capability_types:
            for agent in self.agents.values():
                for capability in agent.capabilities:
                    if capability.capability_type in capability_types:
                        cap_dict = capability.to_dict()
                        # Adjust detail level
                        if detail_level == "basic":
                            # Remove detailed information
                            cap_dict.pop("performance_metrics", None)
                            cap_dict.pop("limitations", None)
                            cap_dict.pop("parameters", None)
                        elif detail_level == "detailed":
                            # Keep most information but summarize metrics
                            if "performance_metrics" in cap_dict:
                                performance_metrics[capability.capability_id] = cap_dict.pop(
                                    "performance_metrics"
                                )
                            if "limitations" in cap_dict:
                                limitations[capability.capability_id] = cap_dict.pop(
                                    "limitations"
                                )
                        # For "full" detail level, keep everything

                        capabilities.append(cap_dict)
        else:
            # Return all capabilities
            for agent in self.agents.values():
                for capability in agent.capabilities:
                    cap_dict = capability.to_dict()
                    # Adjust detail level as above
                    if detail_level == "basic":
                        cap_dict.pop("performance_metrics", None)
                        cap_dict.pop("limitations", None)
                        cap_dict.pop("parameters", None)
                    elif detail_level == "detailed":
                        if "performance_metrics" in cap_dict:
                            performance_metrics[capability.capability_id] = cap_dict.pop(
                                "performance_metrics"
                            )
                        if "limitations" in cap_dict:
                            limitations[capability.capability_id] = cap_dict.pop(
                                "limitations"
                            )

                    capabilities.append(cap_dict)

        # Send the response
        return await self.protocol.send_capability_response(
            request_id=message.message_id,
            recipient=message.sender,
            capabilities=capabilities,
            performance_metrics=performance_metrics if detail_level != "basic" else None,
            limitations=limitations if detail_level != "basic" else None,
        )

    async def broadcast_agent_discovery(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        status: str = "active",
        resources: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Broadcast an agent discovery message to all agents.

        This method sends an agent discovery message to a designated
        recipient (often a registry service or broadcast address).

        Args:
            agent_id: ID of the agent being advertised
            agent_type: Type/role of the agent
            capabilities: List of capability names
            status: Current operational status
            resources: Available resources and constraints
            metadata: Additional agent-specific information

        Returns:
            The message ID of the discovery message, or None if no message was sent
        """
        if not self.protocol:
            logger.error("Cannot broadcast agent discovery: no protocol available")
            return None

        # Use "registry" as the recipient for the broadcast
        # In a real system, this might be a special address or service
        recipient = "registry"

        return await self.protocol.announce_discovery(
            recipient=recipient,
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            status=status,
            resources=resources,
            metadata=metadata,
        )

    async def request_agent_capabilities(
        self,
        recipient: str,
        capability_types: Optional[List[str]] = None,
        detail_level: str = "basic",
    ) -> Optional[str]:
        """Request capabilities from another agent.

        This method sends a capability request message to another agent.

        Args:
            recipient: ID of the agent to request capabilities from
            capability_types: Optional list of capability types to filter by
            detail_level: Level of detail requested (basic, detailed, full)

        Returns:
            The message ID of the request, or None if no message was sent
        """
        if not self.protocol:
            logger.error("Cannot request agent capabilities: no protocol available")
            return None

        return await self.protocol.request_capabilities(
            recipient=recipient,
            capability_types=capability_types,
            detail_level=detail_level,
        )