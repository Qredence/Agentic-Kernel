"""
Core base agent functionality.

This module contains the BaseAgent abstract class that defines the core
functionality and interface for all agents in the system.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, TypedDict

from ...communication.message import MessageType
from ...communication.protocol import CommunicationProtocol, MessageBus
from ...config import AgentConfig
from ...types import Task


class TaskCapability(TypedDict):
    """Definition of a task capability that an agent can perform."""

    name: str
    description: str
    parameters: dict[str, dict[str, Any]]
    required_parameters: list[str]
    optional_parameters: list[str]
    examples: list[dict[str, Any]]
    constraints: list[str]


class AgentCapabilities(TypedDict):
    """Definition of an agent's capabilities."""

    agent_id: str
    agent_name: str
    agent_description: str
    supported_tasks: list[TaskCapability]
    supported_queries: list[str]
    api_version: str


class BaseAgent(ABC):
    """
    Base class for all agents in the system.
    
    This abstract class defines the core functionality and interface that all
    agents must implement. It provides methods for task execution, message
    handling, and agent-to-agent communication.
    """

    def __init__(self, config: AgentConfig, message_bus: MessageBus | None = None):
        """
        Initialize the base agent.
        
        Args:
            config: Configuration for the agent
            message_bus: Optional message bus for agent communication
        """
        self.config = config
        self.id = config.id or str(uuid.uuid4())
        self.name = config.name
        self.description = config.description
        self.capabilities = config.capabilities or []
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{self.id}")
        
        # Set up communication
        self.message_bus = message_bus
        if self.message_bus:
            self._setup_message_handlers()
            
        self.protocol = CommunicationProtocol()
        
        # Initialize task tracking
        self.tasks_received = 0
        self.tasks_completed = 0
        self.tasks_failed = 0
        
        # Performance tracking
        self.execution_times = []
        self.last_execution_time = None

    def _setup_message_handlers(self):
        """Set up handlers for different message types."""
        if not self.message_bus:
            return
            
        # Register message handlers
        self.message_bus.register_handler(
            self.id, MessageType.TASK_REQUEST, self._handle_task_request,
        )
        self.message_bus.register_handler(
            self.id, MessageType.QUERY, self._handle_query,
        )
        self.message_bus.register_handler(
            self.id, MessageType.CAPABILITY_REQUEST, self._handle_capability_request,
        )

    @abstractmethod
    def execute(self, task: Task) -> dict[str, Any]:
        """
        Execute a task and return the result.
        
        Args:
            task: The task to execute
            
        Returns:
            The result of the task execution
        """
        self.tasks_received += 1
        start_time = datetime.now()
        
        try:
            # Validate and preprocess the task
            self.validate_task(task)
            preprocessed_task = self.preprocess_task(task)
            
            # Execute the task (to be implemented by subclasses)
            result = self._execute_task(preprocessed_task)
            
            # Postprocess the result
            final_result = self.postprocess_result(result)
            
            self.tasks_completed += 1
            return final_result
        except Exception as e:
            self.tasks_failed += 1
            self.logger.error(f"Task execution failed: {str(e)}")
            return {"status": "error", "message": str(e)}
        finally:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.execution_times.append(execution_time)
            self.last_execution_time = execution_time

    @abstractmethod
    def _execute_task(self, task: Task) -> dict[str, Any]:
        """
        Internal method to execute a task.
        
        This method must be implemented by subclasses to provide the actual
        task execution logic.
        
        Args:
            task: The preprocessed task to execute
            
        Returns:
            The raw result of the task execution
        """
        pass

    @abstractmethod
    def handle_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Handle a query and return the response.
        
        Args:
            query: The query string
            context: Additional context for the query
            
        Returns:
            The response to the query
        """
        pass

    def _get_supported_tasks(self) -> list[TaskCapability]:
        """
        Get the list of tasks supported by this agent.
        
        Returns:
            List of task capabilities
        """
        return [
            TaskCapability(
                name=capability,
                description=f"Capability to {capability}",
                parameters={},
                required_parameters=[],
                optional_parameters=[],
                examples=[],
                constraints=[],
            )
            for capability in self.capabilities
        ]

    def validate_task(self, task: Task) -> None:
        """
        Validate that a task can be executed by this agent.
        
        Args:
            task: The task to validate
            
        Raises:
            ValueError: If the task is invalid or cannot be executed
        """
        if not task.task_type:
            raise ValueError("Task type is required")
            
        if task.task_type not in self.capabilities:
            raise ValueError(
                f"Task type '{task.task_type}' is not supported by this agent. "
                f"Supported types: {', '.join(self.capabilities)}",
            )
            
        # Additional validation can be implemented by subclasses

    def preprocess_task(self, task: Task) -> Task:
        """
        Preprocess a task before execution.
        
        This method can be overridden by subclasses to perform any necessary
        preprocessing of the task before execution.
        
        Args:
            task: The task to preprocess
            
        Returns:
            The preprocessed task
        """
        # Default implementation returns the task unchanged
        return task

    def postprocess_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Postprocess the result of a task execution.
        
        This method can be overridden by subclasses to perform any necessary
        postprocessing of the result after execution.
        
        Args:
            result: The raw result from task execution
            
        Returns:
            The postprocessed result
        """
        # Default implementation returns the result unchanged
        return result

    def get_capabilities(self) -> AgentCapabilities:
        """
        Get the capabilities of this agent.
        
        Returns:
            The agent's capabilities
        """
        return AgentCapabilities(
            agent_id=self.id,
            agent_name=self.name,
            agent_description=self.description,
            supported_tasks=self._get_supported_tasks(),
            supported_queries=[],  # To be implemented by subclasses
            api_version="1.0",
        )