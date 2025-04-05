"""Base agent class for the Agentic-Kernel system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..config import AgentConfig
from ..types import Task


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(self, config: AgentConfig):
        """Initialize the base agent.
        
        Args:
            config: Agent configuration object
        """
        self.config = config
        self.type = self.__class__.__name__.lower().replace("agent", "")

    @abstractmethod
    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a task.
        
        Args:
            task: Task object containing the task details
            
        Returns:
            Dictionary containing task execution results
        """
        pass

    async def validate_task(self, task: Task) -> bool:
        """Validate if the agent can handle the given task.
        
        Args:
            task: Task object to validate
            
        Returns:
            True if the agent can handle the task, False otherwise
        """
        return task.agent_type == self.type

    async def preprocess_task(self, task: Task) -> Task:
        """Preprocess a task before execution.
        
        Args:
            task: Task object to preprocess
            
        Returns:
            Preprocessed task object
        """
        return task

    async def postprocess_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess the task execution result.
        
        Args:
            result: Task execution result
            
        Returns:
            Postprocessed result
        """
        return result

    def get_capabilities(self) -> Dict[str, Any]:
        """Get the agent's capabilities.
        
        Returns:
            Dictionary describing the agent's capabilities
        """
        return {
            "type": self.type,
            "supported_tasks": self._get_supported_tasks(),
            "config": self.config.dict(),
        }

    def _get_supported_tasks(self) -> Dict[str, Any]:
        """Get the tasks supported by this agent.
        
        Returns:
            Dictionary describing supported tasks
        """
        return {}
