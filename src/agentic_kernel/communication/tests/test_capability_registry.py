"""Tests for the capability registry module.

This module contains tests for the agent capability advertisement and
discovery mechanisms implemented in the capability_registry module.
"""

import asyncio
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from ..capability_registry import (
    AgentCapability,
    AgentInfo,
    CapabilityRegistry,
)
from ..message import AgentDiscoveryMessage, CapabilityRequestMessage, MessageType
from ..protocol import CommunicationProtocol


class TestAgentCapability(unittest.TestCase):
    """Tests for the AgentCapability class."""

    def test_init(self):
        """Test initialization of an agent capability."""
        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            capability_type="reasoning",
            parameters={"param1": "value1"},
            performance_metrics={"accuracy": 0.95},
            limitations={"max_tokens": 1000},
            version="1.0.0",
        )

        self.assertEqual(capability.name, "test_capability")
        self.assertEqual(capability.description, "A test capability")
        self.assertEqual(capability.capability_type, "reasoning")
        self.assertEqual(capability.parameters, {"param1": "value1"})
        self.assertEqual(capability.performance_metrics, {"accuracy": 0.95})
        self.assertEqual(capability.limitations, {"max_tokens": 1000})
        self.assertEqual(capability.version, "1.0.0")
        self.assertIsNotNone(capability.capability_id)
        self.assertIsInstance(capability.last_updated, datetime)

    def test_to_dict(self):
        """Test conversion of a capability to a dictionary."""
        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            capability_type="reasoning",
        )
        capability_dict = capability.to_dict()

        self.assertEqual(capability_dict["name"], "test_capability")
        self.assertEqual(capability_dict["description"], "A test capability")
        self.assertEqual(capability_dict["capability_type"], "reasoning")
        self.assertEqual(capability_dict["parameters"], {})
        self.assertEqual(capability_dict["performance_metrics"], {})
        self.assertEqual(capability_dict["limitations"], {})
        self.assertEqual(capability_dict["version"], "1.0.0")
        self.assertIn("capability_id", capability_dict)
        self.assertIn("last_updated", capability_dict)

    def test_from_dict(self):
        """Test creation of a capability from a dictionary."""
        capability_dict = {
            "capability_id": "test-id",
            "name": "test_capability",
            "description": "A test capability",
            "capability_type": "reasoning",
            "parameters": {"param1": "value1"},
            "performance_metrics": {"accuracy": 0.95},
            "limitations": {"max_tokens": 1000},
            "version": "1.0.0",
            "last_updated": datetime.utcnow().isoformat(),
        }
        capability = AgentCapability.from_dict(capability_dict)

        self.assertEqual(capability.capability_id, "test-id")
        self.assertEqual(capability.name, "test_capability")
        self.assertEqual(capability.description, "A test capability")
        self.assertEqual(capability.capability_type, "reasoning")
        self.assertEqual(capability.parameters, {"param1": "value1"})
        self.assertEqual(capability.performance_metrics, {"accuracy": 0.95})
        self.assertEqual(capability.limitations, {"max_tokens": 1000})
        self.assertEqual(capability.version, "1.0.0")
        self.assertIsInstance(capability.last_updated, datetime)


class TestAgentInfo(unittest.TestCase):
    """Tests for the AgentInfo class."""

    def test_init(self):
        """Test initialization of agent information."""
        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            capability_type="reasoning",
        )
        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type="assistant",
            capabilities=[capability],
            status="active",
            resources={"cpu": 2},
            metadata={"created_by": "test"},
        )

        self.assertEqual(agent_info.agent_id, "test-agent")
        self.assertEqual(agent_info.agent_type, "assistant")
        self.assertEqual(len(agent_info.capabilities), 1)
        self.assertEqual(agent_info.capabilities[0].name, "test_capability")
        self.assertEqual(agent_info.status, "active")
        self.assertEqual(agent_info.resources, {"cpu": 2})
        self.assertEqual(agent_info.metadata, {"created_by": "test"})
        self.assertIsInstance(agent_info.last_seen, datetime)

    def test_to_dict(self):
        """Test conversion of agent info to a dictionary."""
        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            capability_type="reasoning",
        )
        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type="assistant",
            capabilities=[capability],
        )
        agent_dict = agent_info.to_dict()

        self.assertEqual(agent_dict["agent_id"], "test-agent")
        self.assertEqual(agent_dict["agent_type"], "assistant")
        self.assertEqual(len(agent_dict["capabilities"]), 1)
        self.assertEqual(agent_dict["capabilities"][0]["name"], "test_capability")
        self.assertEqual(agent_dict["status"], "active")
        self.assertEqual(agent_dict["resources"], {})
        self.assertEqual(agent_dict["metadata"], {})
        self.assertIn("last_seen", agent_dict)

    def test_from_dict(self):
        """Test creation of agent info from a dictionary."""
        capability_dict = {
            "capability_id": "test-cap-id",
            "name": "test_capability",
            "description": "A test capability",
            "capability_type": "reasoning",
            "parameters": {},
            "performance_metrics": {},
            "limitations": {},
            "version": "1.0.0",
            "last_updated": datetime.utcnow().isoformat(),
        }
        agent_dict = {
            "agent_id": "test-agent",
            "agent_type": "assistant",
            "capabilities": [capability_dict],
            "status": "active",
            "resources": {"cpu": 2},
            "metadata": {"created_by": "test"},
            "last_seen": datetime.utcnow().isoformat(),
        }
        agent_info = AgentInfo.from_dict(agent_dict)

        self.assertEqual(agent_info.agent_id, "test-agent")
        self.assertEqual(agent_info.agent_type, "assistant")
        self.assertEqual(len(agent_info.capabilities), 1)
        self.assertEqual(agent_info.capabilities[0].name, "test_capability")
        self.assertEqual(agent_info.status, "active")
        self.assertEqual(agent_info.resources, {"cpu": 2})
        self.assertEqual(agent_info.metadata, {"created_by": "test"})
        self.assertIsInstance(agent_info.last_seen, datetime)

    def test_add_capability(self):
        """Test adding a capability to an agent."""
        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type="assistant",
        )
        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            capability_type="reasoning",
        )
        agent_info.add_capability(capability)

        self.assertEqual(len(agent_info.capabilities), 1)
        self.assertEqual(agent_info.capabilities[0].name, "test_capability")

        # Test replacing an existing capability
        updated_capability = AgentCapability(
            name="updated_capability",
            description="An updated capability",
            capability_type="reasoning",
        )
        updated_capability.capability_id = capability.capability_id
        agent_info.add_capability(updated_capability)

        self.assertEqual(len(agent_info.capabilities), 1)
        self.assertEqual(agent_info.capabilities[0].name, "updated_capability")

    def test_remove_capability(self):
        """Test removing a capability from an agent."""
        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            capability_type="reasoning",
        )
        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type="assistant",
            capabilities=[capability],
        )

        # Test removing an existing capability
        result = agent_info.remove_capability(capability.capability_id)
        self.assertTrue(result)
        self.assertEqual(len(agent_info.capabilities), 0)

        # Test removing a non-existent capability
        result = agent_info.remove_capability("non-existent-id")
        self.assertFalse(result)

    def test_get_capability_by_id(self):
        """Test getting a capability by ID."""
        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            capability_type="reasoning",
        )
        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type="assistant",
            capabilities=[capability],
        )

        # Test getting an existing capability
        result = agent_info.get_capability_by_id(capability.capability_id)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "test_capability")

        # Test getting a non-existent capability
        result = agent_info.get_capability_by_id("non-existent-id")
        self.assertIsNone(result)

    def test_get_capabilities_by_type(self):
        """Test getting capabilities by type."""
        capability1 = AgentCapability(
            name="reasoning_capability",
            description="A reasoning capability",
            capability_type="reasoning",
        )
        capability2 = AgentCapability(
            name="planning_capability",
            description="A planning capability",
            capability_type="planning",
        )
        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type="assistant",
            capabilities=[capability1, capability2],
        )

        # Test getting capabilities of a specific type
        result = agent_info.get_capabilities_by_type("reasoning")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "reasoning_capability")

        # Test getting capabilities of a non-existent type
        result = agent_info.get_capabilities_by_type("non-existent-type")
        self.assertEqual(len(result), 0)


class TestCapabilityRegistry(unittest.IsolatedAsyncioTestCase):
    """Tests for the CapabilityRegistry class."""

    async def test_register_agent(self):
        """Test registering an agent with the registry."""
        registry = CapabilityRegistry()
        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            capability_type="reasoning",
        )
        agent_info = await registry.register_agent(
            agent_id="test-agent",
            agent_type="assistant",
            capabilities=[capability],
            status="active",
            resources={"cpu": 2},
            metadata={"created_by": "test"},
        )

        self.assertEqual(agent_info.agent_id, "test-agent")
        self.assertEqual(agent_info.agent_type, "assistant")
        self.assertEqual(len(agent_info.capabilities), 1)
        self.assertEqual(agent_info.capabilities[0].name, "test_capability")
        self.assertEqual(agent_info.status, "active")
        self.assertEqual(agent_info.resources, {"cpu": 2})
        self.assertEqual(agent_info.metadata, {"created_by": "test"})

        # Check that the agent was added to the registry
        self.assertIn("test-agent", registry.agents)
        self.assertEqual(registry.agents["test-agent"], agent_info)

    async def test_update_agent(self):
        """Test updating an agent's information."""
        registry = CapabilityRegistry()
        await registry.register_agent(
            agent_id="test-agent",
            agent_type="assistant",
        )

        # Test updating an existing agent
        updated_info = await registry.update_agent(
            agent_id="test-agent",
            status="inactive",
            resources={"cpu": 4},
            metadata={"updated_by": "test"},
        )

        self.assertIsNotNone(updated_info)
        self.assertEqual(updated_info.status, "inactive")
        self.assertEqual(updated_info.resources, {"cpu": 4})
        self.assertEqual(updated_info.metadata, {"updated_by": "test"})

        # Test updating a non-existent agent
        result = await registry.update_agent(
            agent_id="non-existent-agent",
            status="active",
        )
        self.assertIsNone(result)

    async def test_unregister_agent(self):
        """Test unregistering an agent from the registry."""
        registry = CapabilityRegistry()
        await registry.register_agent(
            agent_id="test-agent",
            agent_type="assistant",
        )

        # Test unregistering an existing agent
        result = await registry.unregister_agent("test-agent")
        self.assertTrue(result)
        self.assertNotIn("test-agent", registry.agents)

        # Test unregistering a non-existent agent
        result = await registry.unregister_agent("non-existent-agent")
        self.assertFalse(result)

    async def test_get_agent_info(self):
        """Test getting information about an agent."""
        registry = CapabilityRegistry()
        await registry.register_agent(
            agent_id="test-agent",
            agent_type="assistant",
        )

        # Test getting info for an existing agent
        agent_info = await registry.get_agent_info("test-agent")
        self.assertIsNotNone(agent_info)
        self.assertEqual(agent_info.agent_id, "test-agent")
        self.assertEqual(agent_info.agent_type, "assistant")

        # Test getting info for a non-existent agent
        agent_info = await registry.get_agent_info("non-existent-agent")
        self.assertIsNone(agent_info)

    async def test_add_agent_capability(self):
        """Test adding a capability to an agent."""
        registry = CapabilityRegistry()
        await registry.register_agent(
            agent_id="test-agent",
            agent_type="assistant",
        )

        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            capability_type="reasoning",
        )

        # Test adding a capability to an existing agent
        agent_info = await registry.add_agent_capability("test-agent", capability)
        self.assertIsNotNone(agent_info)
        self.assertEqual(len(agent_info.capabilities), 1)
        self.assertEqual(agent_info.capabilities[0].name, "test_capability")

        # Test adding a capability to a non-existent agent
        result = await registry.add_agent_capability("non-existent-agent", capability)
        self.assertIsNone(result)

    async def test_remove_agent_capability(self):
        """Test removing a capability from an agent."""
        registry = CapabilityRegistry()
        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            capability_type="reasoning",
        )
        await registry.register_agent(
            agent_id="test-agent",
            agent_type="assistant",
            capabilities=[capability],
        )

        # Test removing a capability from an existing agent
        agent_info = await registry.remove_agent_capability(
            "test-agent", capability.capability_id
        )
        self.assertIsNotNone(agent_info)
        self.assertEqual(len(agent_info.capabilities), 0)

        # Test removing a capability from a non-existent agent
        result = await registry.remove_agent_capability(
            "non-existent-agent", capability.capability_id
        )
        self.assertIsNone(result)

    async def test_get_agents_by_capability_type(self):
        """Test getting agents by capability type."""
        registry = CapabilityRegistry()
        capability1 = AgentCapability(
            name="reasoning_capability",
            description="A reasoning capability",
            capability_type="reasoning",
        )
        capability2 = AgentCapability(
            name="planning_capability",
            description="A planning capability",
            capability_type="planning",
        )
        await registry.register_agent(
            agent_id="agent1",
            agent_type="assistant",
            capabilities=[capability1],
        )
        await registry.register_agent(
            agent_id="agent2",
            agent_type="assistant",
            capabilities=[capability2],
        )

        # Test getting agents with a specific capability type
        agents = await registry.get_agents_by_capability_type("reasoning")
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0].agent_id, "agent1")

        # Test getting agents with a non-existent capability type
        agents = await registry.get_agents_by_capability_type("non-existent-type")
        self.assertEqual(len(agents), 0)

    async def test_get_agents_by_status(self):
        """Test getting agents by status."""
        registry = CapabilityRegistry()
        await registry.register_agent(
            agent_id="agent1",
            agent_type="assistant",
            status="active",
        )
        await registry.register_agent(
            agent_id="agent2",
            agent_type="assistant",
            status="inactive",
        )

        # Test getting agents with a specific status
        agents = await registry.get_agents_by_status("active")
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0].agent_id, "agent1")

        # Test getting agents with a non-existent status
        agents = await registry.get_agents_by_status("non-existent-status")
        self.assertEqual(len(agents), 0)

    async def test_get_all_agents(self):
        """Test getting all registered agents."""
        registry = CapabilityRegistry()
        await registry.register_agent(
            agent_id="agent1",
            agent_type="assistant",
        )
        await registry.register_agent(
            agent_id="agent2",
            agent_type="assistant",
        )

        agents = await registry.get_all_agents()
        self.assertEqual(len(agents), 2)
        agent_ids = [agent.agent_id for agent in agents]
        self.assertIn("agent1", agent_ids)
        self.assertIn("agent2", agent_ids)

    @patch("logging.Logger.info")
    async def test_handle_agent_discovery_message(self, mock_logger):
        """Test handling an agent discovery message."""
        registry = CapabilityRegistry()
        
        # Create a mock message
        message = MagicMock(spec=AgentDiscoveryMessage)
        message.content = {
            "agent_id": "test-agent",
            "agent_type": "assistant",
            "capabilities": ["reasoning", "planning"],
            "status": "active",
            "resources": {"cpu": 2},
            "metadata": {"created_by": "test"},
        }

        await registry.handle_agent_discovery_message(message)

        # Check that the agent was registered
        self.assertIn("test-agent", registry.agents)
        agent_info = registry.agents["test-agent"]
        self.assertEqual(agent_info.agent_id, "test-agent")
        self.assertEqual(agent_info.agent_type, "assistant")
        self.assertEqual(len(agent_info.capabilities), 2)
        capability_names = [cap.name for cap in agent_info.capabilities]
        self.assertIn("reasoning", capability_names)
        self.assertIn("planning", capability_names)
        self.assertEqual(agent_info.status, "active")
        self.assertEqual(agent_info.resources, {"cpu": 2})
        self.assertEqual(agent_info.metadata, {"created_by": "test"})

        # Check that the logger was called
        mock_logger.assert_called_with("Processed agent discovery message from test-agent")

    @patch.object(CommunicationProtocol, "send_capability_response")
    async def test_handle_capability_request_message(self, mock_send_response):
        """Test handling a capability request message."""
        # Set up the mock to return a message ID
        mock_send_response.return_value = "response-id"

        # Create a protocol mock
        protocol = MagicMock(spec=CommunicationProtocol)
        protocol.send_capability_response = mock_send_response

        registry = CapabilityRegistry(protocol=protocol)
        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            capability_type="reasoning",
        )
        await registry.register_agent(
            agent_id="test-agent",
            agent_type="assistant",
            capabilities=[capability],
        )

        # Create a mock message
        message = MagicMock(spec=CapabilityRequestMessage)
        message.message_id = "request-id"
        message.sender = "requesting-agent"
        message.content = {
            "capability_types": ["reasoning"],
            "detail_level": "basic",
        }

        response_id = await registry.handle_capability_request_message(message)

        # Check that the response was sent
        self.assertEqual(response_id, "response-id")
        mock_send_response.assert_called_once()
        call_args = mock_send_response.call_args[1]
        self.assertEqual(call_args["request_id"], "request-id")
        self.assertEqual(call_args["recipient"], "requesting-agent")
        self.assertEqual(len(call_args["capabilities"]), 1)
        self.assertEqual(call_args["capabilities"][0]["name"], "test_capability")

    @patch.object(CommunicationProtocol, "announce_discovery")
    async def test_broadcast_agent_discovery(self, mock_announce):
        """Test broadcasting an agent discovery message."""
        # Set up the mock to return a message ID
        mock_announce.return_value = "discovery-id"

        # Create a protocol mock
        protocol = MagicMock(spec=CommunicationProtocol)
        protocol.announce_discovery = mock_announce

        registry = CapabilityRegistry(protocol=protocol)

        message_id = await registry.broadcast_agent_discovery(
            agent_id="test-agent",
            agent_type="assistant",
            capabilities=["reasoning", "planning"],
            status="active",
            resources={"cpu": 2},
            metadata={"created_by": "test"},
        )

        # Check that the discovery message was sent
        self.assertEqual(message_id, "discovery-id")
        mock_announce.assert_called_once()
        call_args = mock_announce.call_args[1]
        self.assertEqual(call_args["recipient"], "registry")
        self.assertEqual(call_args["agent_id"], "test-agent")
        self.assertEqual(call_args["agent_type"], "assistant")
        self.assertEqual(call_args["capabilities"], ["reasoning", "planning"])
        self.assertEqual(call_args["status"], "active")
        self.assertEqual(call_args["resources"], {"cpu": 2})
        self.assertEqual(call_args["metadata"], {"created_by": "test"})

    @patch.object(CommunicationProtocol, "request_capabilities")
    async def test_request_agent_capabilities(self, mock_request):
        """Test requesting capabilities from another agent."""
        # Set up the mock to return a message ID
        mock_request.return_value = "request-id"

        # Create a protocol mock
        protocol = MagicMock(spec=CommunicationProtocol)
        protocol.request_capabilities = mock_request

        registry = CapabilityRegistry(protocol=protocol)

        message_id = await registry.request_agent_capabilities(
            recipient="test-agent",
            capability_types=["reasoning"],
            detail_level="detailed",
        )

        # Check that the request was sent
        self.assertEqual(message_id, "request-id")
        mock_request.assert_called_once()
        call_args = mock_request.call_args[1]
        self.assertEqual(call_args["recipient"], "test-agent")
        self.assertEqual(call_args["capability_types"], ["reasoning"])
        self.assertEqual(call_args["detail_level"], "detailed")


if __name__ == "__main__":
    unittest.main()