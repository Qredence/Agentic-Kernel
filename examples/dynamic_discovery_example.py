"""Example demonstrating dynamic agent discovery and capability advertisement.

This example shows how to use the DynamicCapabilityRegistry to implement
dynamic agent discovery and capability advertisement. It creates multiple
agents that register their capabilities, discover other agents, and receive
notifications when new capabilities become available.
"""

import asyncio
import logging

from agentic_kernel.communication import (
    AgentCapability,
    CommunicationProtocol,
    DynamicCapabilityRegistry,
    Message,
    MessageType,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SimpleCommunicationProtocol(CommunicationProtocol):
    """Simple implementation of the CommunicationProtocol for demonstration purposes."""

    def __init__(self):
        """Initialize the protocol."""
        self.message_handlers = {}
        self.next_message_id = 1

    async def send_message(self, message: Message) -> str:
        """Send a message to its recipient.
        
        Args:
            message: The message to send
            
        Returns:
            The message ID
        """
        logger.info(f"Sending message: {message.message_type.value} from {message.sender} to {message.recipient}")
        
        # In a real implementation, this would send the message over a network
        # For this example, we'll just call the handler directly
        if message.recipient in self.message_handlers:
            await self.message_handlers[message.recipient](message)
        
        return message.message_id

    async def register_message_handler(
        self, agent_id: str, handler: callable,
    ) -> None:
        """Register a handler for incoming messages.
        
        Args:
            agent_id: ID of the agent registering the handler
            handler: Function to call when a message is received
        """
        self.message_handlers[agent_id] = handler

    async def announce_discovery(
        self,
        recipient: str,
        agent_id: str,
        agent_type: str,
        capabilities: list[str],
        status: str = "active",
        resources: dict | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Announce agent discovery.
        
        Args:
            recipient: ID of the recipient
            agent_id: ID of the agent being announced
            agent_type: Type of the agent
            capabilities: List of capability names
            status: Agent status
            resources: Agent resources
            metadata: Agent metadata
            
        Returns:
            The message ID
        """
        message_id = f"discovery-{self.next_message_id}"
        self.next_message_id += 1
        
        message = Message(
            message_id=message_id,
            message_type=MessageType.AGENT_DISCOVERY,
            sender=agent_id,
            recipient=recipient,
            content={
                "agent_id": agent_id,
                "agent_type": agent_type,
                "capabilities": capabilities,
                "status": status,
                "resources": resources or {},
                "metadata": metadata or {},
            },
        )
        
        await self.send_message(message)
        return message_id

    async def send_capability_response(
        self,
        request_id: str | None,
        recipient: str,
        capabilities: list[dict],
        performance_metrics: dict | None = None,
        limitations: dict | None = None,
        notification: bool = False,
    ) -> str:
        """Send a capability response.
        
        Args:
            request_id: ID of the request being responded to
            recipient: ID of the recipient
            capabilities: List of capability dictionaries
            performance_metrics: Performance metrics for capabilities
            limitations: Limitations of capabilities
            notification: Whether this is a notification (not a response)
            
        Returns:
            The message ID
        """
        message_id = f"capability-response-{self.next_message_id}"
        self.next_message_id += 1
        
        message = Message(
            message_id=message_id,
            message_type=MessageType.CAPABILITY_RESPONSE,
            sender="registry",
            recipient=recipient,
            content={
                "capabilities": capabilities,
                "performance_metrics": performance_metrics or {},
                "limitations": limitations or {},
                "is_notification": notification,
            },
            correlation_id=request_id,
        )
        
        await self.send_message(message)
        return message_id

    async def request_capabilities(
        self,
        recipient: str,
        capability_types: list[str] | None = None,
        detail_level: str = "basic",
    ) -> str:
        """Request capabilities from an agent.
        
        Args:
            recipient: ID of the recipient
            capability_types: Types of capabilities to request
            detail_level: Level of detail to request
            
        Returns:
            The message ID
        """
        message_id = f"capability-request-{self.next_message_id}"
        self.next_message_id += 1
        
        message = Message(
            message_id=message_id,
            message_type=MessageType.CAPABILITY_REQUEST,
            sender="requester",
            recipient=recipient,
            content={
                "capability_types": capability_types,
                "detail_level": detail_level,
            },
        )
        
        await self.send_message(message)
        return message_id


class SimpleAgent:
    """Simple agent implementation for demonstration purposes."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        registry: DynamicCapabilityRegistry,
    ):
        """Initialize the agent.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of the agent
            registry: Capability registry to use
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.registry = registry
        self.capabilities = []
        self.discovered_capabilities = []
        
    async def register(self):
        """Register the agent with the registry."""
        await self.registry.register_agent(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            capabilities=self.capabilities,
        )
        logger.info(f"Agent {self.agent_id} registered with {len(self.capabilities)} capabilities")
        
    async def add_capability(self, name: str, description: str, capability_type: str):
        """Add a capability to the agent.
        
        Args:
            name: Name of the capability
            description: Description of the capability
            capability_type: Type of the capability
        """
        capability = AgentCapability(
            name=name,
            description=description,
            capability_type=capability_type,
        )
        self.capabilities.append(capability)
        
        # Update the registry
        await self.registry.add_agent_capability(self.agent_id, capability)
        logger.info(f"Agent {self.agent_id} added capability: {name}")
        
    async def discover_capabilities(self, capability_types=None):
        """Discover capabilities from other agents.
        
        Args:
            capability_types: Types of capabilities to discover
        """
        capabilities = await self.registry.discover_capabilities(
            requester_id=self.agent_id,
            capability_types=capability_types,
        )
        
        self.discovered_capabilities = capabilities
        logger.info(f"Agent {self.agent_id} discovered {len(capabilities)} capabilities")
        
        for cap in capabilities:
            logger.info(f"  - {cap['name']} ({cap['capability_type']}) from {cap['agent_id']}")
        
    async def subscribe_to_capabilities(self, capability_types=None):
        """Subscribe to capability updates.
        
        Args:
            capability_types: Types of capabilities to subscribe to
        """
        subscription_index = await self.registry.subscribe_to_capabilities(
            subscriber_id=self.agent_id,
            capability_types=capability_types,
            callback=self.capability_update_callback,
        )
        
        logger.info(f"Agent {self.agent_id} subscribed to capability updates (index: {subscription_index})")
        
    def capability_update_callback(self, capability, agent_id):
        """Callback for capability updates.
        
        Args:
            capability: The updated capability
            agent_id: ID of the agent with the capability
        """
        logger.info(f"Agent {self.agent_id} received capability update: {capability.name} from {agent_id}")


async def main():
    """Run the example."""
    # Create the communication protocol
    protocol = SimpleCommunicationProtocol()
    
    # Create the dynamic capability registry
    registry = DynamicCapabilityRegistry(
        protocol=protocol,
        broadcast_interval=10,  # Broadcast every 10 seconds for the example
        presence_timeout=30,    # Consider agents inactive after 30 seconds
    )
    
    # Start the registry
    await registry.start()
    
    try:
        # Create some agents
        agents = [
            SimpleAgent(f"agent-{i}", f"type-{i % 3}", registry)
            for i in range(5)
        ]
        
        # Register the agents
        for agent in agents:
            await agent.register()
        
        # Add capabilities to the agents
        await agents[0].add_capability(
            "reasoning", "General reasoning capability", "reasoning",
        )
        await agents[1].add_capability(
            "planning", "Task planning capability", "planning",
        )
        await agents[2].add_capability(
            "learning", "Machine learning capability", "learning",
        )
        await agents[3].add_capability(
            "perception", "Perception capability", "perception",
        )
        await agents[4].add_capability(
            "memory", "Memory management capability", "memory",
        )
        
        # Let agents discover capabilities
        for agent in agents:
            await agent.discover_capabilities()
        
        # Subscribe to capability updates
        for agent in agents:
            await agent.subscribe_to_capabilities()
        
        # Add a new capability to demonstrate subscription notifications
        logger.info("\nAdding new capability to demonstrate subscription notifications:")
        await agents[0].add_capability(
            "advanced-reasoning", "Advanced reasoning capability", "reasoning",
        )
        
        # Wait for a while to see periodic broadcasts
        logger.info("\nWaiting for periodic broadcasts...")
        await asyncio.sleep(15)
        
        # Add another capability
        logger.info("\nAdding another capability:")
        await agents[2].add_capability(
            "deep-learning", "Deep learning capability", "learning",
        )
        
        # Wait a bit more
        await asyncio.sleep(5)
        
    finally:
        # Stop the registry
        await registry.stop()


if __name__ == "__main__":
    asyncio.run(main())