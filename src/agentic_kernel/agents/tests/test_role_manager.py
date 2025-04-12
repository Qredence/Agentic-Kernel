"""Tests for the role manager module.

This module contains tests for the agent specialization and role assignment
functionality implemented in the role_manager module.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from ...communication.capability_registry import AgentCapability, AgentInfo, CapabilityRegistry
from ..role_manager import AgentRole, RoleManager


class TestAgentRole(unittest.TestCase):
    """Tests for the AgentRole class."""

    def test_init(self):
        """Test initialization of an agent role."""
        role = AgentRole(
            name="Data Processor",
            description="Processes and transforms data",
            required_capabilities={"data_processing", "file_handling"},
            preferred_capabilities={"data_visualization"},
            metadata={"priority": "high"},
        )

        self.assertEqual(role.role_id, "data_processor")
        self.assertEqual(role.name, "Data Processor")
        self.assertEqual(role.description, "Processes and transforms data")
        self.assertEqual(role.required_capabilities, {"data_processing", "file_handling"})
        self.assertEqual(role.preferred_capabilities, {"data_visualization"})
        self.assertEqual(role.metadata, {"priority": "high"})

    def test_to_dict(self):
        """Test conversion of a role to a dictionary."""
        role = AgentRole(
            name="Data Processor",
            description="Processes and transforms data",
            required_capabilities={"data_processing", "file_handling"},
        )
        role_dict = role.to_dict()

        self.assertEqual(role_dict["role_id"], "data_processor")
        self.assertEqual(role_dict["name"], "Data Processor")
        self.assertEqual(role_dict["description"], "Processes and transforms data")
        self.assertEqual(set(role_dict["required_capabilities"]), {"data_processing", "file_handling"})
        self.assertEqual(role_dict["preferred_capabilities"], [])
        self.assertEqual(role_dict["metadata"], {})

    def test_from_dict(self):
        """Test creation of a role from a dictionary."""
        role_dict = {
            "role_id": "data_processor",
            "name": "Data Processor",
            "description": "Processes and transforms data",
            "required_capabilities": ["data_processing", "file_handling"],
            "preferred_capabilities": ["data_visualization"],
            "metadata": {"priority": "high"},
        }
        role = AgentRole.from_dict(role_dict)

        self.assertEqual(role.role_id, "data_processor")
        self.assertEqual(role.name, "Data Processor")
        self.assertEqual(role.description, "Processes and transforms data")
        self.assertEqual(role.required_capabilities, {"data_processing", "file_handling"})
        self.assertEqual(role.preferred_capabilities, {"data_visualization"})
        self.assertEqual(role.metadata, {"priority": "high"})

    def test_is_compatible_with_agent(self):
        """Test checking if an agent is compatible with a role."""
        role = AgentRole(
            name="Data Processor",
            description="Processes and transforms data",
            required_capabilities={"data_processing", "file_handling"},
        )

        # Create agent capabilities
        cap1 = AgentCapability(
            name="Data Processing",
            description="Processes data",
            capability_type="data_processing",
        )
        cap2 = AgentCapability(
            name="File Handling",
            description="Handles files",
            capability_type="file_handling",
        )
        cap3 = AgentCapability(
            name="Data Visualization",
            description="Visualizes data",
            capability_type="data_visualization",
        )

        # Create agent with all required capabilities
        agent1 = AgentInfo(
            agent_id="agent1",
            agent_type="processor",
            capabilities=[cap1, cap2, cap3],
        )

        # Create agent with some required capabilities
        agent2 = AgentInfo(
            agent_id="agent2",
            agent_type="processor",
            capabilities=[cap1],
        )

        # Create agent with no required capabilities
        agent3 = AgentInfo(
            agent_id="agent3",
            agent_type="processor",
            capabilities=[cap3],
        )

        # Test compatibility
        self.assertTrue(role.is_compatible_with_agent(agent1))
        self.assertFalse(role.is_compatible_with_agent(agent2))
        self.assertFalse(role.is_compatible_with_agent(agent3))

    def test_get_compatibility_score(self):
        """Test calculating compatibility score for an agent with a role."""
        role = AgentRole(
            name="Data Processor",
            description="Processes and transforms data",
            required_capabilities={"data_processing", "file_handling"},
            preferred_capabilities={"data_visualization", "data_analysis"},
        )

        # Create agent capabilities
        cap1 = AgentCapability(
            name="Data Processing",
            description="Processes data",
            capability_type="data_processing",
        )
        cap2 = AgentCapability(
            name="File Handling",
            description="Handles files",
            capability_type="file_handling",
        )
        cap3 = AgentCapability(
            name="Data Visualization",
            description="Visualizes data",
            capability_type="data_visualization",
        )

        # Create agent with all required and some preferred capabilities
        agent1 = AgentInfo(
            agent_id="agent1",
            agent_type="processor",
            capabilities=[cap1, cap2, cap3],
        )

        # Create agent with all required but no preferred capabilities
        agent2 = AgentInfo(
            agent_id="agent2",
            agent_type="processor",
            capabilities=[cap1, cap2],
        )

        # Create agent with some required capabilities
        agent3 = AgentInfo(
            agent_id="agent3",
            agent_type="processor",
            capabilities=[cap1],
        )

        # Test compatibility scores
        self.assertEqual(role.get_compatibility_score(agent1), 0.75)  # 3/4 capabilities
        self.assertEqual(role.get_compatibility_score(agent2), 0.5)   # 2/4 capabilities
        self.assertEqual(role.get_compatibility_score(agent3), 0.0)   # Not compatible


class TestRoleManager(unittest.IsolatedAsyncioTestCase):
    """Tests for the RoleManager class."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        # Create mock capability registry
        self.registry = MagicMock(spec=CapabilityRegistry)
        
        # Create role manager
        self.role_manager = RoleManager(self.registry)
        
        # Create test roles
        self.role1 = AgentRole(
            name="Data Processor",
            description="Processes and transforms data",
            required_capabilities={"data_processing", "file_handling"},
        )
        self.role2 = AgentRole(
            name="Data Analyzer",
            description="Analyzes data",
            required_capabilities={"data_analysis"},
        )
        
        # Add roles to manager
        self.role_manager.add_role(self.role1)
        self.role_manager.add_role(self.role2)
        
        # Create agent capabilities
        self.cap1 = AgentCapability(
            name="Data Processing",
            description="Processes data",
            capability_type="data_processing",
        )
        self.cap2 = AgentCapability(
            name="File Handling",
            description="Handles files",
            capability_type="file_handling",
        )
        self.cap3 = AgentCapability(
            name="Data Analysis",
            description="Analyzes data",
            capability_type="data_analysis",
        )
        
        # Create test agents
        self.agent1 = AgentInfo(
            agent_id="agent1",
            agent_type="processor",
            capabilities=[self.cap1, self.cap2],
        )
        self.agent2 = AgentInfo(
            agent_id="agent2",
            agent_type="analyzer",
            capabilities=[self.cap3],
        )
        self.agent3 = AgentInfo(
            agent_id="agent3",
            agent_type="processor",
            capabilities=[self.cap1, self.cap2, self.cap3],
        )

    def test_add_role(self):
        """Test adding a role to the manager."""
        role = AgentRole(
            name="New Role",
            description="A new role",
            required_capabilities={"new_capability"},
        )
        self.role_manager.add_role(role)
        
        self.assertIn("new_role", self.role_manager.roles)
        self.assertEqual(self.role_manager.roles["new_role"], role)

    def test_remove_role(self):
        """Test removing a role from the manager."""
        # Add role to an agent first
        self.role_manager.agent_roles["agent1"] = ["data_processor"]
        
        # Remove the role
        result = self.role_manager.remove_role("data_processor")
        
        self.assertTrue(result)
        self.assertNotIn("data_processor", self.role_manager.roles)
        self.assertNotIn("data_processor", self.role_manager.agent_roles["agent1"])
        
        # Test removing non-existent role
        result = self.role_manager.remove_role("non_existent_role")
        self.assertFalse(result)

    def test_get_role(self):
        """Test getting a role by ID."""
        role = self.role_manager.get_role("data_processor")
        self.assertEqual(role, self.role1)
        
        # Test getting non-existent role
        role = self.role_manager.get_role("non_existent_role")
        self.assertIsNone(role)

    def test_get_all_roles(self):
        """Test getting all roles."""
        roles = self.role_manager.get_all_roles()
        self.assertEqual(len(roles), 2)
        self.assertIn(self.role1, roles)
        self.assertIn(self.role2, roles)

    async def test_assign_role_to_agent(self):
        """Test assigning a role to an agent."""
        # Mock get_agent_info to return our test agent
        self.registry.get_agent_info = AsyncMock(return_value=self.agent1)
        
        # Assign role to agent
        result = await self.role_manager.assign_role_to_agent("agent1", "data_processor")
        
        self.assertTrue(result)
        self.assertIn("agent1", self.role_manager.agent_roles)
        self.assertIn("data_processor", self.role_manager.agent_roles["agent1"])
        
        # Test assigning non-existent role
        result = await self.role_manager.assign_role_to_agent("agent1", "non_existent_role")
        self.assertFalse(result)
        
        # Test assigning to non-existent agent
        self.registry.get_agent_info = AsyncMock(return_value=None)
        result = await self.role_manager.assign_role_to_agent("non_existent_agent", "data_processor")
        self.assertFalse(result)
        
        # Test assigning incompatible role
        self.registry.get_agent_info = AsyncMock(return_value=self.agent2)
        result = await self.role_manager.assign_role_to_agent("agent2", "data_processor")
        self.assertFalse(result)

    async def test_unassign_role_from_agent(self):
        """Test unassigning a role from an agent."""
        # Assign role to agent first
        self.role_manager.agent_roles["agent1"] = ["data_processor"]
        
        # Unassign role
        result = await self.role_manager.unassign_role_from_agent("agent1", "data_processor")
        
        self.assertTrue(result)
        self.assertNotIn("data_processor", self.role_manager.agent_roles["agent1"])
        
        # Test unassigning non-existent role
        result = await self.role_manager.unassign_role_from_agent("agent1", "non_existent_role")
        self.assertFalse(result)
        
        # Test unassigning from non-existent agent
        result = await self.role_manager.unassign_role_from_agent("non_existent_agent", "data_processor")
        self.assertFalse(result)

    async def test_get_agent_roles(self):
        """Test getting all roles assigned to an agent."""
        # Assign roles to agent
        self.role_manager.agent_roles["agent1"] = ["data_processor", "data_analyzer"]
        
        # Get agent roles
        roles = await self.role_manager.get_agent_roles("agent1")
        
        self.assertEqual(len(roles), 2)
        self.assertIn(self.role1, roles)
        self.assertIn(self.role2, roles)
        
        # Test getting roles for non-existent agent
        roles = await self.role_manager.get_agent_roles("non_existent_agent")
        self.assertEqual(roles, [])

    async def test_find_agents_for_role(self):
        """Test finding agents compatible with a role."""
        # Mock get_all_agents to return our test agents
        self.registry.get_all_agents = AsyncMock(return_value=[self.agent1, self.agent2, self.agent3])
        
        # Find agents for role
        agents = await self.role_manager.find_agents_for_role("data_processor")
        
        self.assertEqual(len(agents), 2)
        agent_ids = [agent[0].agent_id for agent in agents]
        self.assertIn("agent1", agent_ids)
        self.assertIn("agent3", agent_ids)
        
        # Test finding agents for non-existent role
        agents = await self.role_manager.find_agents_for_role("non_existent_role")
        self.assertEqual(agents, [])

    async def test_auto_assign_roles(self):
        """Test automatically assigning roles to agents."""
        # Mock get_all_agents to return our test agents
        self.registry.get_all_agents = AsyncMock(return_value=[self.agent1, self.agent2, self.agent3])
        
        # Auto-assign roles
        assignments = await self.role_manager.auto_assign_roles()
        
        self.assertEqual(len(assignments), 3)
        self.assertIn("agent1", assignments)
        self.assertIn("agent2", assignments)
        self.assertIn("agent3", assignments)
        
        self.assertIn("data_processor", assignments["agent1"])
        self.assertIn("data_analyzer", assignments["agent2"])
        self.assertIn("data_processor", assignments["agent3"])
        self.assertIn("data_analyzer", assignments["agent3"])

    async def test_find_best_agent_for_role(self):
        """Test finding the best agent for a role."""
        # Mock find_agents_for_role to return scored agents
        self.role_manager.find_agents_for_role = AsyncMock(
            return_value=[(self.agent3, 1.0), (self.agent1, 0.5)]
        )
        
        # Find best agent
        best_agent = await self.role_manager.find_best_agent_for_role("data_processor")
        
        self.assertIsNotNone(best_agent)
        self.assertEqual(best_agent[0].agent_id, "agent3")
        self.assertEqual(best_agent[1], 1.0)
        
        # Test finding best agent when no agents are compatible
        self.role_manager.find_agents_for_role = AsyncMock(return_value=[])
        best_agent = await self.role_manager.find_best_agent_for_role("data_processor")
        self.assertIsNone(best_agent)


if __name__ == "__main__":
    unittest.main()