"""
Enhanced agent implementation combining all core functionality.

This module provides an EnhancedAgent class that combines all the core
functionality from the base agent and various mixins into a single,
comprehensive agent implementation.
"""

from abc import abstractmethod
from typing import Any

from ...communication.message import MessageType
from ...communication.protocol import MessageBus
from ...config import AgentConfig
from ...types import Task
from .base_agent import BaseAgent
from .consensus import ConsensusMixin
from .feedback import FeedbackMixin
from .message_handling import MessageHandlingMixin


class EnhancedAgent(BaseAgent, MessageHandlingMixin, ConsensusMixin, FeedbackMixin):
    """
    Enhanced agent implementation combining all core functionality.
    
    This class combines the core BaseAgent functionality with message handling,
    consensus building, and feedback processing capabilities. It provides a
    comprehensive agent implementation that can be extended for specific use cases.
    """
    
    def __init__(self, config: AgentConfig, message_bus: MessageBus | None = None):
        """
        Initialize the enhanced agent.
        
        Args:
            config: Configuration for the agent
            message_bus: Optional message bus for agent communication
        """
        # Initialize the base agent
        BaseAgent.__init__(self, config, message_bus)
        
        # Set up additional message handlers for consensus and feedback
        if self.message_bus:
            self.message_bus.register_handler(
                self.id, MessageType.CONSENSUS_REQUEST, self._handle_consensus_request,
            )
            self.message_bus.register_handler(
                self.id, MessageType.CONSENSUS_VOTE, self._handle_consensus_vote,
            )
            self.message_bus.register_handler(
                self.id, MessageType.CONSENSUS_RESULT, self._handle_consensus_result,
            )
            self.message_bus.register_handler(
                self.id, MessageType.FEEDBACK, self._handle_feedback,
            )
    
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
        
        This method must be implemented by subclasses to provide query handling logic.
        
        Args:
            query: The query string
            context: Additional context for the query
            
        Returns:
            The response to the query
        """
        pass


class SimpleEnhancedAgent(EnhancedAgent):
    """
    A simple implementation of the EnhancedAgent with basic task execution and query handling.
    
    This class provides a concrete implementation of the abstract methods in EnhancedAgent,
    making it ready to use for simple agent tasks.
    """
    
    def _execute_task(self, task: Task) -> dict[str, Any]:
        """
        Execute a task with basic functionality.
        
        Args:
            task: The task to execute
            
        Returns:
            The result of the task execution
        """
        self.logger.info(f"Executing task: {task.description}")
        
        # Simple implementation - in a real agent, this would contain more complex logic
        return {
            "status": "completed",
            "message": f"Task '{task.description}' executed successfully",
            "task_id": task.task_id,
            "task_type": task.task_type,
        }
    
    def handle_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Handle a query with basic functionality.
        
        Args:
            query: The query string
            context: Additional context for the query
            
        Returns:
            The response to the query
        """
        self.logger.info(f"Handling query: {query}")
        
        # Simple implementation - in a real agent, this would contain more complex logic
        return {
            "status": "completed",
            "response": f"Processed query: {query}",
            "context_keys": list(context.keys()) if context else [],
        }