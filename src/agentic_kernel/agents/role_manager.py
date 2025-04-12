"""Agent specialization and role assignment based on capabilities.

This module implements a role management system for agents, allowing them to be
assigned specialized roles based on their capabilities. It provides mechanisms
for defining roles with specific capability requirements and assigning agents
to roles based on their advertised capabilities.

Key features:
1. Role definition with capability requirements
2. Role assignment based on agent capabilities
3. Role-based task delegation
4. Role compatibility checking
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from ..communication.capability_registry import AgentCapability, AgentInfo, CapabilityRegistry

logger = logging.getLogger(__name__)


class AgentRole:
    """Definition of an agent role with capability requirements.

    This class represents a specialized role that an agent can fulfill,
    including the capabilities required for the role and any additional
    metadata.

    Attributes:
        role_id: Unique identifier for the role
        name: Name of the role
        description: Description of what the role entails
        required_capabilities: Set of capability types required for this role
        preferred_capabilities: Set of capability types preferred but not required
        metadata: Additional role-specific metadata
    """

    def __init__(
        self,
        name: str,
        description: str,
        required_capabilities: Set[str],
        preferred_capabilities: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a role.

        Args:
            name: Name of the role
            description: Description of what the role entails
            required_capabilities: Set of capability types required for this role
            preferred_capabilities: Set of capability types preferred but not required
            metadata: Additional role-specific metadata
        """
        self.role_id = name.lower().replace(" ", "_")
        self.name = name
        self.description = description
        self.required_capabilities = required_capabilities
        self.preferred_capabilities = preferred_capabilities or set()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert the role to a dictionary.

        Returns:
            Dictionary representation of the role
        """
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "required_capabilities": list(self.required_capabilities),
            "preferred_capabilities": list(self.preferred_capabilities),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentRole":
        """Create a role from a dictionary.

        Args:
            data: Dictionary representation of the role

        Returns:
            AgentRole instance
        """
        role = cls(
            name=data["name"],
            description=data["description"],
            required_capabilities=set(data["required_capabilities"]),
            preferred_capabilities=set(data.get("preferred_capabilities", [])),
            metadata=data.get("metadata", {}),
        )
        role.role_id = data["role_id"]
        return role

    def is_compatible_with_agent(self, agent_info: AgentInfo) -> bool:
        """Check if an agent is compatible with this role.

        Args:
            agent_info: Information about the agent

        Returns:
            True if the agent has all required capabilities, False otherwise
        """
        agent_capability_types = {cap.capability_type for cap in agent_info.capabilities}
        return self.required_capabilities.issubset(agent_capability_types)

    def get_compatibility_score(self, agent_info: AgentInfo) -> float:
        """Calculate a compatibility score for an agent with this role.

        The score is based on how many of the required and preferred
        capabilities the agent has. A score of 1.0 means the agent has
        all required and preferred capabilities.

        Args:
            agent_info: Information about the agent

        Returns:
            Compatibility score between 0.0 and 1.0
        """
        if not self.is_compatible_with_agent(agent_info):
            return 0.0

        agent_capability_types = {cap.capability_type for cap in agent_info.capabilities}
        
        # Calculate score based on required and preferred capabilities
        total_capabilities = len(self.required_capabilities) + len(self.preferred_capabilities)
        if total_capabilities == 0:
            return 1.0  # No capabilities required, so any agent is fully compatible
        
        matched_capabilities = len(self.required_capabilities)  # We know all required are matched
        matched_capabilities += len(self.preferred_capabilities.intersection(agent_capability_types))
        
        return matched_capabilities / total_capabilities


class RoleManager:
    """Manager for agent roles and role assignment.

    This class provides functionality for defining roles, assigning roles
    to agents based on their capabilities, and finding agents for specific
    roles.

    Attributes:
        roles: Dictionary mapping role IDs to role definitions
        registry: Reference to the capability registry
    """

    def __init__(self, registry: CapabilityRegistry):
        """Initialize the role manager.

        Args:
            registry: Reference to the capability registry
        """
        self.roles: Dict[str, AgentRole] = {}
        self.registry = registry
        self.agent_roles: Dict[str, List[str]] = {}  # Maps agent IDs to assigned role IDs

    def add_role(self, role: AgentRole) -> None:
        """Add a role definition.

        Args:
            role: The role to add
        """
        self.roles[role.role_id] = role
        logger.info(f"Added role {role.name} with ID {role.role_id}")

    def remove_role(self, role_id: str) -> bool:
        """Remove a role definition.

        Args:
            role_id: ID of the role to remove

        Returns:
            True if the role was removed, False if not found
        """
        if role_id in self.roles:
            del self.roles[role_id]
            
            # Remove this role from all agents
            for agent_id in self.agent_roles:
                if role_id in self.agent_roles[agent_id]:
                    self.agent_roles[agent_id].remove(role_id)
            
            logger.info(f"Removed role with ID {role_id}")
            return True
        return False

    def get_role(self, role_id: str) -> Optional[AgentRole]:
        """Get a role by its ID.

        Args:
            role_id: ID of the role to get

        Returns:
            The role if found, None otherwise
        """
        return self.roles.get(role_id)

    def get_all_roles(self) -> List[AgentRole]:
        """Get all defined roles.

        Returns:
            List of all roles
        """
        return list(self.roles.values())

    async def assign_role_to_agent(self, agent_id: str, role_id: str) -> bool:
        """Assign a role to an agent.

        Args:
            agent_id: ID of the agent
            role_id: ID of the role to assign

        Returns:
            True if the role was assigned, False if not compatible or not found
        """
        # Check if role exists
        role = self.get_role(role_id)
        if not role:
            logger.warning(f"Role {role_id} not found")
            return False

        # Get agent info
        agent_info = await self.registry.get_agent_info(agent_id)
        if not agent_info:
            logger.warning(f"Agent {agent_id} not found in registry")
            return False

        # Check compatibility
        if not role.is_compatible_with_agent(agent_info):
            logger.warning(f"Agent {agent_id} is not compatible with role {role_id}")
            return False

        # Assign role
        if agent_id not in self.agent_roles:
            self.agent_roles[agent_id] = []
        
        if role_id not in self.agent_roles[agent_id]:
            self.agent_roles[agent_id].append(role_id)
            logger.info(f"Assigned role {role_id} to agent {agent_id}")
        
        return True

    async def unassign_role_from_agent(self, agent_id: str, role_id: str) -> bool:
        """Unassign a role from an agent.

        Args:
            agent_id: ID of the agent
            role_id: ID of the role to unassign

        Returns:
            True if the role was unassigned, False if not assigned
        """
        if agent_id in self.agent_roles and role_id in self.agent_roles[agent_id]:
            self.agent_roles[agent_id].remove(role_id)
            logger.info(f"Unassigned role {role_id} from agent {agent_id}")
            return True
        return False

    async def get_agent_roles(self, agent_id: str) -> List[AgentRole]:
        """Get all roles assigned to an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            List of roles assigned to the agent
        """
        if agent_id not in self.agent_roles:
            return []
        
        return [self.roles[role_id] for role_id in self.agent_roles[agent_id] 
                if role_id in self.roles]

    async def find_agents_for_role(self, role_id: str) -> List[Tuple[AgentInfo, float]]:
        """Find agents that are compatible with a role.

        Args:
            role_id: ID of the role

        Returns:
            List of tuples containing agent info and compatibility score,
            sorted by score in descending order
        """
        role = self.get_role(role_id)
        if not role:
            logger.warning(f"Role {role_id} not found")
            return []

        # Get all agents
        agents = await self.registry.get_all_agents()
        
        # Filter and score compatible agents
        compatible_agents = []
        for agent in agents:
            if role.is_compatible_with_agent(agent):
                score = role.get_compatibility_score(agent)
                compatible_agents.append((agent, score))
        
        # Sort by score in descending order
        return sorted(compatible_agents, key=lambda x: x[1], reverse=True)

    async def auto_assign_roles(self) -> Dict[str, List[str]]:
        """Automatically assign roles to agents based on capabilities.

        This method analyzes all agents and roles, and assigns roles to
        agents based on their capabilities. Each agent may be assigned
        multiple roles if compatible.

        Returns:
            Dictionary mapping agent IDs to lists of assigned role IDs
        """
        # Get all agents and roles
        agents = await self.registry.get_all_agents()
        roles = self.get_all_roles()
        
        # Merge new assignments with existing ones
        for agent in agents:
            if agent.agent_id not in self.agent_roles:
                self.agent_roles[agent.agent_id] = []
            existing_roles = set(self.agent_roles[agent.agent_id])
            for role in roles:
                if role.is_compatible_with_agent(agent) and role.role_id not in existing_roles:
                    logger.info(f"Auto-assigned role {role.role_id} to agent {agent.agent_id}")
        
        return self.agent_roles

    async def find_best_agent_for_role(self, role_id: str) -> Optional[Tuple[AgentInfo, float]]:
        """Find the best agent for a specific role.

        Args:
            role_id: ID of the role

        Returns:
            Tuple containing the best agent info and its compatibility score,
            or None if no compatible agent is found
        """
        compatible_agents = await self.find_agents_for_role(role_id)
        if not compatible_agents:
            return None
        
        return compatible_agents[0]  # Return the highest-scoring agent