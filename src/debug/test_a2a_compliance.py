"""Test script to verify A2A compliance.

This script tests the A2A compliance of the Agentic-Kernel framework by:
1. Creating two agents
2. Having one agent discover the capabilities of the other
3. Verifying that the capability discovery works as expected
"""

import asyncio
import logging
import sys
from typing import Dict, List, Any, Optional

# Add the src directory to the Python path
sys.path.append("src")

from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.communication.message import Message, MessageType
from agentic_kernel.communication.protocol import CommunicationProtocol, MessageBus
from agentic_kernel.communication.capability_registry import CapabilityRegistry, AgentCapability

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TestAgent(BaseAgent):
    """A simple agent for testing A2A compliance."""

    def __init__(self, agent_id: str, capabilities: List[str]):
        """Initialize the test agent.
        
        Args:
            agent_id: ID of the agent
            capabilities: List of capability names
        """
        self.agent_id = agent_id
        self.capability_names = capabilities
        self.message_bus = MessageBus()
        self.protocol = CommunicationProtocol(agent_id, self.message_bus)
        self.capability_registry = CapabilityRegistry(self.protocol)
        self.received_capabilities: List[Dict[str, Any]] = []

        # Register message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self):
        """Set up message handlers for different message types."""
        self.protocol.register_handler(
            MessageType.CAPABILITY_REQUEST, self._handle_capability_request
        )
        self.protocol.register_handler(
            MessageType.CAPABILITY_RESPONSE, self._handle_capability_response
        )

    async def _handle_capability_request(self, message: Message):
        """Handle a capability request message."""
        logger.info(f"Agent {self.agent_id} received capability request from {message.sender}")
        await self.capability_registry.handle_capability_request_message(message)

    async def _handle_capability_response(self, message: Message):
        """Handle a capability response message."""
        logger.info(f"Agent {self.agent_id} received capability response from {message.sender}")
        self.received_capabilities = message.content.get("capabilities", [])

    async def register_capabilities(self):
        """Register the agent's capabilities."""
        for cap_name in self.capability_names:
            capability = AgentCapability(
                name=cap_name,
                description=f"Capability: {cap_name}",
                capability_type=cap_name,
            )
            await self.capability_registry.add_agent_capability(self.agent_id, capability)

    async def request_capabilities(self, recipient: str, capability_types: Optional[List[str]] = None):
        """Request capabilities from another agent."""
        logger.info(f"Agent {self.agent_id} requesting capabilities from {recipient}")
        await self.capability_registry.request_agent_capabilities(
            recipient=recipient,
            capability_types=capability_types,
            detail_level="full"
        )

    def get_capabilities(self) -> List[Dict[str, Any]]:
        """Get the agent's capabilities.
        
        Returns:
            List of capability dictionaries
        """
        return self.received_capabilities


async def main():
    """Run the A2A compliance test."""
    # Create two agents with different capabilities
    agent1 = TestAgent("agent1", ["reasoning", "planning", "capability_discovery"])
    agent2 = TestAgent("agent2", ["learning", "perception", "agent_discovery"])

    # Register capabilities
    await agent1.register_capabilities()
    await agent2.register_capabilities()

    # Have agent1 request capabilities from agent2
    await agent1.request_capabilities("agent2")

    # Wait for the capability response to be processed
    await asyncio.sleep(1)

    # Verify that agent1 received agent2's capabilities
    received_capabilities = agent1.get_capabilities()
    logger.info(f"Agent1 received capabilities: {received_capabilities}")

    # Check if the received capabilities match agent2's capabilities
    capability_names = [cap.get("name") for cap in received_capabilities]
    expected_names = agent2.capability_names

    if all(name in capability_names for name in expected_names):
        logger.info("A2A compliance test PASSED: All expected capabilities were received")
    else:
        logger.error(f"A2A compliance test FAILED: Expected {expected_names}, got {capability_names}")


if __name__ == "__main__":
    asyncio.run(main())
