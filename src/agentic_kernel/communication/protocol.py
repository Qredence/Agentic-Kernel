"""Protocol implementation for agent communication.

This module implements the communication protocol used between agents in the
Agentic-Kernel system. It provides the core functionality for message passing,
routing, and handling.

Key features:
1. Message routing
2. Asynchronous communication
3. Message validation
4. Error handling
5. Delivery guarantees
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime
import logging

from .message import (
    Message,
    MessageType,
    MessagePriority,
    TaskRequest,
    TaskResponse,
    Query,
    QueryResponse,
    StatusUpdate,
    ErrorMessage,
)

logger = logging.getLogger(__name__)


class MessageBus:
    """Central message bus for routing messages between agents.

    This class implements the core message routing functionality,
    ensuring messages are delivered to their intended recipients.

    Attributes:
        subscribers: Dictionary mapping agent IDs to their message handlers
        message_queue: Queue for asynchronous message processing
    """

    def __init__(self):
        """Initialize the message bus."""
        self.subscribers: Dict[str, Callable[[Message], Awaitable[None]]] = {}
        self.message_queue: asyncio.Queue[Message] = asyncio.Queue()
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the message processing loop."""
        if self._running:
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._process_messages())
        logger.info("Message bus started")

    async def stop(self):
        """Stop the message processing loop."""
        if not self._running:
            return

        self._running = False
        if self._processor_task:
            await self._processor_task
        logger.info("Message bus stopped")

    def subscribe(self, agent_id: str, handler: Callable[[Message], Awaitable[None]]):
        """Subscribe an agent to receive messages.

        Args:
            agent_id: Unique identifier for the agent
            handler: Async function to handle received messages
        """
        self.subscribers[agent_id] = handler
        logger.debug(f"Agent {agent_id} subscribed to message bus")

    def unsubscribe(self, agent_id: str):
        """Unsubscribe an agent from receiving messages.

        Args:
            agent_id: ID of the agent to unsubscribe
        """
        if agent_id in self.subscribers:
            del self.subscribers[agent_id]
            logger.debug(f"Agent {agent_id} unsubscribed from message bus")

    async def publish(self, message: Message):
        """Publish a message to the bus.

        Args:
            message: Message to publish
        """
        await self.message_queue.put(message)
        logger.debug(f"Message {message.message_id} queued for delivery")

    async def _process_messages(self):
        """Process messages from the queue."""
        while self._running:
            try:
                message = await self.message_queue.get()

                if message.recipient in self.subscribers:
                    try:
                        await self.subscribers[message.recipient](message)
                        logger.debug(
                            f"Message {message.message_id} delivered to {message.recipient}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error delivering message {message.message_id}: {str(e)}"
                        )
                        # Create error message for sender
                        error_msg = ErrorMessage(
                            message_id=str(uuid.uuid4()),
                            sender="message_bus",
                            recipient=message.sender,
                            content={
                                "error_type": "delivery_failed",
                                "description": f"Failed to deliver message {message.message_id}",
                                "details": str(e),
                            },
                            correlation_id=message.message_id,
                        )
                        await self.message_queue.put(error_msg)
                else:
                    logger.warning(
                        f"No handler found for recipient {message.recipient}"
                    )

                self.message_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")


class CommunicationProtocol:
    """Implementation of the agent communication protocol.

    This class provides the high-level interface for agents to communicate
    with each other through the message bus.

    Attributes:
        agent_id: ID of the agent using this protocol
        message_bus: Reference to the central message bus
        message_handlers: Custom message type handlers
    """

    def __init__(self, agent_id: str, message_bus: MessageBus):
        """Initialize the protocol.

        Args:
            agent_id: ID of the agent using this protocol
            message_bus: Reference to the central message bus
        """
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.message_handlers: Dict[
            MessageType, Callable[[Message], Awaitable[None]]
        ] = {}

        # Register with message bus
        self.message_bus.subscribe(agent_id, self._handle_message)

    async def send_message(
        self,
        recipient: str,
        message_type: MessageType,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
    ) -> str:
        """Send a message to another agent.

        Args:
            recipient: ID of the receiving agent
            message_type: Type of message to send
            content: Message content
            priority: Message priority
            correlation_id: Optional ID to link related messages

        Returns:
            The message ID of the sent message
        """
        message_id = str(uuid.uuid4())
        message = Message(
            message_id=message_id,
            message_type=message_type,
            sender=self.agent_id,
            recipient=recipient,
            content=content,
            priority=priority,
            correlation_id=correlation_id,
        )

        await self.message_bus.publish(message)
        return message_id

    def register_handler(
        self, message_type: MessageType, handler: Callable[[Message], Awaitable[None]]
    ):
        """Register a handler for a specific message type.

        Args:
            message_type: Type of messages to handle
            handler: Async function to handle messages
        """
        self.message_handlers[message_type] = handler
        logger.debug(f"Registered handler for {message_type.value} messages")

    async def _handle_message(self, message: Message):
        """Handle an incoming message.

        Args:
            message: The received message
        """
        if message.message_type in self.message_handlers:
            await self.message_handlers[message.message_type](message)
        else:
            logger.warning(
                f"No handler registered for message type {message.message_type.value}"
            )

    async def request_task(
        self,
        recipient: str,
        task_description: str,
        parameters: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
        deadline: Optional[datetime] = None,
    ) -> str:
        """Request another agent to perform a task.

        Args:
            recipient: ID of the agent to perform the task
            task_description: Description of the task
            parameters: Task parameters
            constraints: Optional execution constraints
            deadline: Optional deadline for completion

        Returns:
            The message ID of the task request
        """
        content = {
            "task_description": task_description,
            "parameters": parameters,
            "constraints": constraints or {},
            "deadline": deadline.isoformat() if deadline else None,
        }

        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.TASK_REQUEST,
            content=content,
            priority=MessagePriority.NORMAL,
        )

    async def send_task_response(
        self,
        request_id: str,
        recipient: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ):
        """Send a response to a task request.

        Args:
            request_id: ID of the original task request
            recipient: ID of the requesting agent
            status: Task execution status
            result: Optional task result
            error: Optional error information
            metrics: Optional performance metrics
        """
        content = {
            "status": status,
            "result": result,
            "error": error,
            "metrics": metrics or {},
        }

        await self.send_message(
            recipient=recipient,
            message_type=MessageType.TASK_RESPONSE,
            content=content,
            correlation_id=request_id,
        )

    async def query_agent(
        self,
        recipient: str,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        required_format: Optional[str] = None,
    ) -> str:
        """Query another agent for information.

        Args:
            recipient: ID of the agent to query
            query: The query string
            context: Optional context information
            required_format: Optional format for the response

        Returns:
            The message ID of the query
        """
        content = {
            "query": query,
            "context": context or {},
            "required_format": required_format,
        }

        return await self.send_message(
            recipient=recipient, message_type=MessageType.QUERY, content=content
        )

    async def send_query_response(
        self,
        query_id: str,
        recipient: str,
        result: Any,
        confidence: float = 1.0,
        source: Optional[str] = None,
    ):
        """Send a response to a query.

        Args:
            query_id: ID of the original query
            recipient: ID of the querying agent
            result: The query result
            confidence: Confidence level in the result
            source: Optional source of the information
        """
        content = {"result": result, "confidence": confidence, "source": source}

        await self.send_message(
            recipient=recipient,
            message_type=MessageType.QUERY_RESPONSE,
            content=content,
            correlation_id=query_id,
        )

    async def send_status_update(
        self,
        recipient: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        resources: Optional[Dict[str, Any]] = None,
    ):
        """Send a status update to another agent.

        Args:
            recipient: ID of the receiving agent
            status: Current status
            details: Optional status details
            resources: Optional resource information
        """
        content = {
            "status": status,
            "details": details or {},
            "resources": resources or {},
        }

        await self.send_message(
            recipient=recipient, message_type=MessageType.STATUS_UPDATE, content=content
        )

    async def send_error(
        self,
        recipient: str,
        error_type: str,
        description: str,
        stack_trace: Optional[str] = None,
        recovery_hints: Optional[List[str]] = None,
    ):
        """Send an error message to another agent.

        Args:
            recipient: ID of the receiving agent
            error_type: Type of error
            description: Error description
            stack_trace: Optional stack trace
            recovery_hints: Optional recovery suggestions
        """
        content = {
            "error_type": error_type,
            "description": description,
            "stack_trace": stack_trace,
            "recovery_hints": recovery_hints or [],
        }

        await self.send_message(
            recipient=recipient,
            message_type=MessageType.ERROR,
            content=content,
            priority=MessagePriority.HIGH,
        )
