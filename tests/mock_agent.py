"""
Mock Agent for Testing Agent Communication Patterns

This module provides a mock agent implementation for testing agent communication patterns
in the Agentic Kernel system. The mock agent can be configured to respond to different
types of messages in specific ways, allowing for controlled testing of agent interactions.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from src.agentic_kernel.agents.base import BaseAgent
from src.agentic_kernel.communication.message import Message, MessageType
from src.agentic_kernel.communication.protocol import MessageBus
from src.agentic_kernel.config import AgentConfig
from src.agentic_kernel.types import Task

logger = logging.getLogger(__name__)

class MockAgent(BaseAgent):
    """
    A mock agent implementation for testing agent communication patterns.
    
    This agent can be configured to respond to different types of messages in specific ways,
    allowing for controlled testing of agent interactions.
    """
    
    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus | None = None,
        config: AgentConfig | None = None,
        capabilities: dict[str, Any] | None = None,
        response_handlers: dict[MessageType, Callable[[Message], Awaitable[None]]] | None = None,
    ):
        """
        Initialize a mock agent.
        
        Args:
            agent_id: The ID of the agent.
            message_bus: The message bus for agent communication.
            config: The agent configuration.
            capabilities: The agent capabilities.
            response_handlers: Custom handlers for different message types.
        """
        if config is None:
            config = AgentConfig(agent_id=agent_id, agent_type="mock")
        
        super().__init__(config, message_bus)
        
        self.capabilities = capabilities or {}
        self.response_handlers = response_handlers or {}
        self.received_messages: list[Message] = []
        self.sent_messages: list[Message] = []
        
        # Override default message handlers with custom ones if provided
        for message_type, handler in self.response_handlers.items():
            self.protocol.register_handler(message_type, handler)
    
    async def execute(self, task: Task) -> dict[str, Any]:
        """
        Execute a task.
        
        This implementation simply logs the task and returns a mock result.
        
        Args:
            task: The task to execute.
            
        Returns:
            A dictionary containing the mock result.
        """
        logger.info(f"MockAgent {self.agent_id} executing task: {task.description}")
        return {"status": "success", "result": f"Mock execution of task: {task.description}"}
    
    async def handle_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Handle a query.
        
        This implementation simply logs the query and returns a mock response.
        
        Args:
            query: The query to handle.
            context: The context for the query.
            
        Returns:
            A dictionary containing the mock response.
        """
        logger.info(f"MockAgent {self.agent_id} handling query: {query}")
        return {"response": f"Mock response to query: {query}", "confidence": 0.9}
    
    def record_message(self, message: Message, is_sent: bool = False) -> None:
        """
        Record a message that was received or sent.
        
        Args:
            message: The message to record.
            is_sent: Whether the message was sent (True) or received (False).
        """
        if is_sent:
            self.sent_messages.append(message)
        else:
            self.received_messages.append(message)
    
    def get_received_messages(self, message_type: MessageType | None = None) -> list[Message]:
        """
        Get all received messages, optionally filtered by message type.
        
        Args:
            message_type: The type of messages to filter for.
            
        Returns:
            A list of received messages.
        """
        if message_type is None:
            return self.received_messages
        return [m for m in self.received_messages if m.message_type == message_type]
    
    def get_sent_messages(self, message_type: MessageType | None = None) -> list[Message]:
        """
        Get all sent messages, optionally filtered by message type.
        
        Args:
            message_type: The type of messages to filter for.
            
        Returns:
            A list of sent messages.
        """
        if message_type is None:
            return self.sent_messages
        return [m for m in self.sent_messages if m.message_type == message_type]
    
    def clear_message_history(self) -> None:
        """
        Clear the message history.
        """
        self.received_messages = []
        self.sent_messages = []
    
    def set_response_handler(
        self, message_type: MessageType, handler: Callable[[Message], Awaitable[None]],
    ) -> None:
        """
        Set a custom response handler for a specific message type.
        
        Args:
            message_type: The type of message to handle.
            handler: The handler function.
        """
        self.response_handlers[message_type] = handler
        self.protocol.register_handler(message_type, handler)
    
    async def _handle_message(self, message: Message) -> None:
        """
        Handle an incoming message.
        
        This method records the message and then delegates to the appropriate handler.
        
        Args:
            message: The message to handle.
        """
        self.record_message(message)
        await super()._handle_message(message)
    
    async def send_message(
        self, recipient: str, message_type: MessageType, content: dict[str, Any], **kwargs,
    ) -> None:
        """
        Send a message to another agent.
        
        This method records the message and then sends it.
        
        Args:
            recipient: The recipient agent ID.
            message_type: The type of message.
            content: The message content.
            **kwargs: Additional message parameters.
        """
        message = await self.protocol.send_message(recipient, message_type, content, **kwargs)
        self.record_message(message, is_sent=True)
    
    def get_capabilities(self) -> dict[str, Any]:
        """
        Get the agent's capabilities.
        
        Returns:
            A dictionary of capabilities.
        """
        return self.capabilities