"""Agent management functionality for the orchestrator.

This module provides the AgentManager class, which is responsible for
registering agents, managing agent specializations, and selecting the
most appropriate agent for a given task.
"""

import logging
from typing import Any

from ..agents import BaseAgent
from ..types import Task
from .agent_selection import AgentSelector

logger = logging.getLogger(__name__)


class AgentManager:
    """Manages agent registration and selection.

    This class is responsible for:
    1. Registering agents with the orchestrator
    2. Managing agent specializations
    3. Selecting the most appropriate agent for a task
    4. Resetting agent state when needed

    Attributes:
        agents: Dictionary of registered agents
        agent_selector: Component for intelligently selecting agents for tasks
    """

    def __init__(self):
        """Initialize the agent manager."""
        self.agents: dict[str, BaseAgent] = {}
        self.agent_selector = AgentSelector()

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator.

        Args:
            agent: Agent instance to register
        """
        self.agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.type} with ID {agent.agent_id}")

    def register_agent_specialization(self, agent_id: str, domains: list[str]) -> None:
        """Register an agent's domain specializations.

        Args:
            agent_id: The ID of the agent
            domains: List of specialized domains
        """
        if agent_id in self.agents:
            self.agent_selector.skill_matrix.register_agent_specialization(
                agent_id, domains,
            )
            logger.info(f"Registered specializations for agent {agent_id}: {domains}")
        else:
            logger.warning(
                f"Cannot register specialization for unknown agent: {agent_id}",
            )

    async def reset_agent_state(self, agent: BaseAgent) -> None:
        """Reset an agent's state.

        Args:
            agent: Agent to reset
        """
        try:
            await agent.reset()
            logger.info(f"Reset state for agent: {agent.type}")
        except Exception as e:
            logger.error(f"Failed to reset agent {agent.type}: {str(e)}")
            raise

    async def select_agent_for_task(
        self, task: Task, context: dict[str, Any] | None = None,
    ) -> BaseAgent | None:
        """Select the best agent for a given task.

        This method uses the agent selector to find the most appropriate
        agent for executing the task based on capabilities and performance.

        Args:
            task: The task to be executed
            context: Optional execution context

        Returns:
            Selected agent instance, or None if no suitable agent found
        """
        # Use the agent selector to find the best agent for this task
        agent_id = await self.agent_selector.select_agent(task, self.agents, context)

        if not agent_id:
            logger.warning(f"No suitable agent found for task: {task.name}")
            return None

        return self.agents.get(agent_id)

    def get_agent_by_id(self, agent_id: str) -> BaseAgent | None:
        """Get an agent by its ID.

        Args:
            agent_id: The ID of the agent to retrieve

        Returns:
            The agent instance, or None if not found
        """
        return self.agents.get(agent_id)

    def get_all_agents(self) -> dict[str, BaseAgent]:
        """Get all registered agents.

        Returns:
            Dictionary of all registered agents
        """
        return self.agents