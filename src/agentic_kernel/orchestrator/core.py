"""Core orchestrator implementation for managing workflow execution."""

import logging
from typing import Dict, Any
from datetime import datetime

from ..agents import BaseAgent
from ..config import AgentConfig
from ..ledgers import TaskLedger, ProgressLedger
from ..types import Task, WorkflowStep

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Agent responsible for orchestrating workflow execution.

    The Orchestrator Agent is responsible for:
    1. Task decomposition and planning
    2. Dynamic plan creation and revision
    3. Task delegation to specialized agents
    4. Progress monitoring and error recovery
    5. Workflow management through nested loops

    Attributes:
        config: Configuration for the orchestrator
        task_ledger: Ledger for tracking tasks
        progress_ledger: Ledger for tracking workflow progress
        agents: Dictionary of registered agents
    """

    def __init__(
        self,
        config: AgentConfig,
        task_ledger: TaskLedger,
        progress_ledger: ProgressLedger,
    ):
        """Initialize the orchestrator.

        Args:
            config: Configuration for the orchestrator
            task_ledger: Task tracking ledger
            progress_ledger: Progress tracking ledger
        """
        self.config = config
        self.task_ledger = task_ledger
        self.progress_ledger = progress_ledger
        self.agents: Dict[str, BaseAgent] = {}
        self.max_planning_attempts = 3
        self.max_inner_loop_iterations = 10
        self.reflection_threshold = 0.7  # Progress threshold before reflection

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator.

        Args:
            agent: Agent instance to register
        """
        self.agents[agent.type] = agent
        logger.info(f"Registered agent: {agent.type}")

    async def _reset_agent_state(self, agent: BaseAgent) -> None:
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
