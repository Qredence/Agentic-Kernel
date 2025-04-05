"""Base agent implementation for AgenticFleet."""

from typing import Optional, Any, Dict
from abc import ABC, abstractmethod

from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str
    model: str
    endpoint: str
    description: Optional[str] = None
    system_message: Optional[str] = None


class BaseAgent:
    """Base class for all agents in AgenticFleet."""
    
    def __init__(self, config: AgentConfig) -> None:
        """Initialize the agent with configuration."""
        self.config = config
        self.name = config.name
    
    async def handle_message(self, message: str) -> str:
        """Handle an incoming message. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement handle_message")


class Agent(ABC):
    """Abstract base class for all agents in the agentic kernel."""

    def __init__(self, name: str, description: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize the agent.

        Args:
            name: The unique name of the agent.
            description: A brief description of the agent's capabilities.
            config: Agent-specific configuration options.
        """
        self.name = name
        self.description = description or ""
        self.config = config or {}

    @abstractmethod
    async def execute_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a given task.

        Args:
            task_description: A description of the task to be performed.
            context: Optional context information relevant to the task (e.g., previous steps, ledger data).

        Returns:
            A dictionary containing the result of the task execution.
            The structure should ideally include keys like 'status' ('success', 'failure'),
            'output', and 'error_message' if applicable.
        """
        pass

    def get_info(self) -> Dict[str, str]:
        """Return basic information about the agent."""
        return {
            "name": self.name,
            "description": self.description
        }
