"""Protocol implementation for agent communication.

This module implements the communication protocol used between agents in the
Agentic-Kernel system. It provides the core functionality for message passing,
routing, and handling.

Key features:
1. Message routing
2. Asynchronous communication
3. Message validation
4. Standardized error handling
5. Delivery guarantees
6. Automatic retries for transient errors
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union, Type

from ..exceptions import (
    AgenticKernelError,
    CommunicationError,
    MessageDeliveryError,
    MessageTimeoutError,
    MessageValidationError,
    ProtocolError,
)
from .error_handler import ErrorHandler
from .message import (
    AgentDiscoveryMessage,
    CapabilityRequestMessage,
    CapabilityResponseMessage,
    ConflictNotificationMessage,
    ConflictResolutionMessage,
    ConsensusRequestMessage,
    ConsensusResultMessage,
    ConsensusVoteMessage,
    CoordinationRequestMessage,
    CoordinationResponseMessage,
    DeliveryConfirmationMessage,
    ErrorMessage,
    FeedbackMessage,
    Message,
    MessageAckMessage,
    MessagePriority,
    MessageRetryMessage,
    MessageType,
    Query,
    QueryResponse,
    StatusUpdate,
    TaskDecompositionMessage,
    TaskRequest,
    TaskResponse,
)

logger = logging.getLogger(__name__)


class MessageBus:
    """Central message bus for routing messages between agents.

    This class implements the core message routing functionality,
    ensuring messages are delivered to their intended recipients.

    Attributes:
        subscribers: Dictionary mapping agent IDs to their message handlers
        message_queue: Queue for asynchronous message processing
        error_handler: Utility for standardized error handling
    """

    def __init__(self):
        """Initialize the message bus."""
        self.subscribers: Dict[str, Callable[[Message], Awaitable[None]]] = {}
        self.message_queue: asyncio.Queue[Message] = asyncio.Queue()
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        self.error_handler = ErrorHandler(max_retries=3, retry_delay=1.0)

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
                        # Convert to MessageDeliveryError if it's not already an AgenticKernelError
                        if not isinstance(e, AgenticKernelError):
                            error = MessageDeliveryError(
                                message=f"Failed to deliver message {message.message_id}: {str(e)}",
                                details={
                                    "message_id": message.message_id,
                                    "sender": message.sender,
                                    "recipient": message.recipient,
                                    "message_type": message.message_type.value,
                                    "original_error": str(e)
                                },
                                retry_possible=True
                            )
                        else:
                            error = e

                        # Log the error with context
                        self.error_handler.log_error(error, {
                            "message_id": message.message_id,
                            "sender": message.sender,
                            "recipient": message.recipient
                        })

                        # Create error message for sender with standardized format
                        error_content = self.error_handler.format_error_message(
                            error, 
                            include_recovery=True,
                            include_stack_trace=False
                        )

                        error_msg = ErrorMessage(
                            message_id=str(uuid.uuid4()),
                            sender="message_bus",
                            recipient=message.sender,
                            content=error_content,
                            correlation_id=message.message_id,
                        )
                        await self.message_queue.put(error_msg)
                else:
                    # Create a standardized error for unknown recipient
                    error = MessageDeliveryError(
                        message=f"No handler found for recipient {message.recipient}",
                        code="UNKNOWN_RECIPIENT",
                        details={
                            "message_id": message.message_id,
                            "sender": message.sender,
                            "recipient": message.recipient,
                            "message_type": message.message_type.value
                        },
                        recovery_hints=[
                            "Verify that the recipient agent ID is correct",
                            "Check if the recipient agent is registered with the message bus",
                            "Ensure the recipient agent is active and running"
                        ],
                        retry_possible=False
                    )

                    self.error_handler.log_error(error)

                    # Create error message for sender
                    error_content = self.error_handler.format_error_message(error)
                    error_msg = ErrorMessage(
                        message_id=str(uuid.uuid4()),
                        sender="message_bus",
                        recipient=message.sender,
                        content=error_content,
                        correlation_id=message.message_id,
                    )
                    await self.message_queue.put(error_msg)

                self.message_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Handle unexpected errors in the message processing loop
                error = ProtocolError(
                    message=f"Error processing message: {str(e)}",
                    code="MESSAGE_PROCESSING_ERROR",
                    details={"original_error": str(e)},
                    retry_possible=False
                )
                self.error_handler.log_error(error)


class CommunicationProtocol:
    """Implementation of the agent communication protocol.

    This class provides the high-level interface for agents to communicate
    with each other through the message bus.

    Attributes:
        agent_id: ID of the agent using this protocol
        message_bus: Reference to the central message bus
        message_handlers: Custom message type handlers
        error_handler: Utility for standardized error handling
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
        self.error_handler = ErrorHandler(max_retries=3, retry_delay=1.0)

        # Message tracking for reliability guarantees
        self.sent_messages: Dict[str, Message] = {}  # Messages sent by this agent
        self.received_messages: Dict[str, Message] = {}  # Messages received by this agent
        self.pending_acknowledgments: Dict[str, Message] = {}  # Messages waiting for acknowledgment
        self.pending_confirmations: Dict[str, Message] = {}  # Messages waiting for delivery confirmation

        # Register with message bus
        self.message_bus.subscribe(agent_id, self._handle_message)

        # Register handlers for reliability-related message types
        self.register_handler(MessageType.MESSAGE_ACK, self._handle_message_ack)
        self.register_handler(MessageType.DELIVERY_CONFIRMATION, self._handle_delivery_confirmation)
        self.register_handler(MessageType.MESSAGE_RETRY, self._handle_message_retry)

    async def send_message(
        self,
        recipient: str,
        message_type: MessageType,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        validate: bool = True,
        requires_acknowledgment: bool = False,
        persistent: bool = False,
        max_delivery_attempts: Optional[int] = None,
        delivery_deadline: Optional[datetime] = None,
        sequence_number: Optional[int] = None,
    ) -> str:
        """Send a message to another agent.

        Args:
            recipient: ID of the receiving agent
            message_type: Type of message to send
            content: Message content
            priority: Message priority
            correlation_id: Optional ID to link related messages
            validate: Whether to validate the message before sending
            requires_acknowledgment: Whether the message requires acknowledgment
            persistent: Whether the message should be persisted
            max_delivery_attempts: Maximum number of delivery attempts
            delivery_deadline: Deadline for message delivery
            sequence_number: Sequence number for ordering messages in a conversation

        Returns:
            The message ID of the sent message

        Raises:
            MessageValidationError: If validation fails and validate=True
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
            requires_acknowledgment=requires_acknowledgment,
            persistent=persistent,
            max_delivery_attempts=max_delivery_attempts,
            delivery_deadline=delivery_deadline,
            sequence_number=sequence_number,
        )

        # Validate message if requested
        if validate:
            try:
                self._validate_message(message)
            except MessageValidationError as e:
                self.error_handler.log_error(e, {
                    "message_type": message_type.value,
                    "recipient": recipient,
                    "sender": self.agent_id
                })
                raise

        # Track the message for reliability guarantees
        self.sent_messages[message_id] = message

        # Track messages requiring acknowledgment
        if requires_acknowledgment:
            self.pending_acknowledgments[message_id] = message

        # Track messages requiring delivery confirmation
        self.pending_confirmations[message_id] = message

        # Use error handler's retry mechanism for publishing
        async def publish_operation():
            await self.message_bus.publish(message)

        try:
            await self.error_handler.with_retries(
                publish_operation,
                retry_exceptions=[CommunicationError],
                context={
                    "message_id": message_id,
                    "message_type": message_type.value,
                    "recipient": recipient,
                    "sender": self.agent_id
                }
            )

            # Increment delivery attempts
            message.delivery_attempts += 1

            # If the message is persistent, store it
            if persistent:
                await self._persist_message(message)

        except Exception as e:
            # Convert to MessageDeliveryError if it's not already an AgenticKernelError
            if not isinstance(e, AgenticKernelError):
                error = MessageDeliveryError(
                    message=f"Failed to send message to {recipient}: {str(e)}",
                    details={
                        "message_id": message_id,
                        "message_type": message_type.value,
                        "recipient": recipient,
                        "sender": self.agent_id,
                        "original_error": str(e)
                    },
                    retry_possible=True
                )
                self.error_handler.log_error(error)
                raise error
            raise

        return message_id

    async def send_acknowledgment(
        self,
        recipient: str,
        original_message_id: str,
        status: str = "received",
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send an acknowledgment message.

        Args:
            recipient: ID of the agent to acknowledge
            original_message_id: ID of the message being acknowledged
            status: Status of the acknowledgment (e.g., "received", "processing", "rejected")
            details: Any additional details about the acknowledgment

        Returns:
            The message ID of the acknowledgment message
        """
        content = {
            "original_message_id": original_message_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {},
        }

        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.MESSAGE_ACK,
            content=content,
            priority=MessagePriority.HIGH,  # Acknowledgments should be high priority
            correlation_id=original_message_id,
        )

    async def send_delivery_confirmation(
        self,
        recipient: str,
        original_message_id: str,
        status: str = "delivered",
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a delivery confirmation message.

        Args:
            recipient: ID of the agent to confirm delivery to
            original_message_id: ID of the message being confirmed
            status: Status of the delivery (e.g., "delivered", "failed")
            details: Any additional details about the delivery

        Returns:
            The message ID of the delivery confirmation message
        """
        content = {
            "original_message_id": original_message_id,
            "delivery_timestamp": datetime.utcnow().isoformat(),
            "recipient_id": self.agent_id,
            "status": status,
            "details": details or {},
        }

        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.DELIVERY_CONFIRMATION,
            content=content,
            priority=MessagePriority.HIGH,  # Delivery confirmations should be high priority
            correlation_id=original_message_id,
        )

    async def request_message_retry(
        self,
        recipient: str,
        original_message_id: str,
        reason: str,
        retry_delay: Optional[float] = None,
    ) -> str:
        """Request retry of a message.

        Args:
            recipient: ID of the agent to request retry from
            original_message_id: ID of the message to retry
            reason: Reason for the retry
            retry_delay: Delay before the next retry attempt

        Returns:
            The message ID of the retry request message
        """
        # Get the original message if we have it
        original_message = self.sent_messages.get(original_message_id)

        content = {
            "original_message_id": original_message_id,
            "reason": reason,
            "retry_count": original_message.delivery_attempts if original_message else 0,
            "max_retries": original_message.max_delivery_attempts if original_message else 3,
            "retry_delay": retry_delay or self.error_handler.retry_delay,
        }

        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.MESSAGE_RETRY,
            content=content,
            priority=MessagePriority.HIGH,  # Retry requests should be high priority
            correlation_id=original_message_id,
        )

    async def _persist_message(self, message: Message) -> None:
        """Persist a message for reliability.

        This method stores a message to ensure it can be recovered in case of system failures.
        In a production system, this would write to a persistent store like a database.

        Args:
            message: The message to persist
        """
        # In a real implementation, this would write to a database or other persistent store
        # For now, we'll just log that we would persist the message
        logger.info(f"Would persist message {message.message_id} (type: {message.message_type.value})")

        # In a real implementation, we might do something like:
        # await self.message_store.save(message.dict())
        pass

    async def check_pending_messages(self) -> None:
        """Check the status of pending acknowledgments and confirmations.

        This method checks for messages that are waiting for acknowledgment or
        delivery confirmation and takes appropriate action based on their status.
        """
        current_time = datetime.utcnow()

        # Check pending acknowledgments
        for message_id, message in list(self.pending_acknowledgments.items()):
            # Check if the message has a delivery deadline
            if message.delivery_deadline and current_time > message.delivery_deadline:
                logger.warning(f"Message {message_id} acknowledgment deadline exceeded")

                # Request retry if max attempts not exceeded
                max_attempts = message.max_delivery_attempts or 3
                if message.delivery_attempts < max_attempts:
                    await self.request_message_retry(
                        recipient=message.recipient,
                        original_message_id=message_id,
                        reason="Acknowledgment timeout",
                    )
                else:
                    logger.error(f"Max delivery attempts exceeded for message {message_id}")
                    # Remove from pending acknowledgments
                    del self.pending_acknowledgments[message_id]

        # Check pending confirmations
        for message_id, message in list(self.pending_confirmations.items()):
            # Check if the message has a delivery deadline
            if message.delivery_deadline and current_time > message.delivery_deadline:
                logger.warning(f"Message {message_id} delivery confirmation deadline exceeded")

                # Request retry if max attempts not exceeded
                max_attempts = message.max_delivery_attempts or 3
                if message.delivery_attempts < max_attempts:
                    await self.request_message_retry(
                        recipient=message.recipient,
                        original_message_id=message_id,
                        reason="Delivery confirmation timeout",
                    )
                else:
                    logger.error(f"Max delivery attempts exceeded for message {message_id}")
                    # Remove from pending confirmations
                    del self.pending_confirmations[message_id]

    def cleanup_old_messages(self, max_age_seconds: int = 3600) -> None:
        """Clean up old messages to prevent memory leaks.

        This method removes messages that are older than the specified age
        and are no longer needed for reliability guarantees.

        Args:
            max_age_seconds: Maximum age of messages to keep in seconds (default: 1 hour)
        """
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(seconds=max_age_seconds)

        # Clean up sent messages
        for message_id, message in list(self.sent_messages.items()):
            # Keep messages that are still pending acknowledgment or confirmation
            if message_id in self.pending_acknowledgments or message_id in self.pending_confirmations:
                continue

            # Remove messages older than the cutoff time
            if message.timestamp < cutoff_time:
                del self.sent_messages[message_id]
                logger.debug(f"Cleaned up old sent message {message_id}")

        # Clean up received messages
        for message_id, message in list(self.received_messages.items()):
            # Remove messages older than the cutoff time
            if message.timestamp < cutoff_time:
                del self.received_messages[message_id]
                logger.debug(f"Cleaned up old received message {message_id}")

    async def start_reliability_monitor(self, check_interval: float = 60.0) -> asyncio.Task:
        """Start a background task to monitor message reliability.

        This method starts a background task that periodically checks pending
        messages and cleans up old messages to ensure reliability guarantees.

        Args:
            check_interval: Interval between checks in seconds (default: 60 seconds)

        Returns:
            The asyncio task for the monitor
        """
        async def monitor_task():
            while True:
                try:
                    # Check pending messages
                    await self.check_pending_messages()

                    # Clean up old messages
                    self.cleanup_old_messages()

                    # Wait for the next check interval
                    await asyncio.sleep(check_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in reliability monitor: {str(e)}")
                    await asyncio.sleep(check_interval)

        # Start the monitor task
        task = asyncio.create_task(monitor_task())
        logger.info(f"Started reliability monitor with check interval {check_interval} seconds")
        return task

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
        # Track received message for reliability guarantees
        self.received_messages[message.message_id] = message

        # Send acknowledgment if required
        if message.requires_acknowledgment and message.message_type != MessageType.MESSAGE_ACK:
            await self.send_acknowledgment(
                recipient=message.sender,
                original_message_id=message.message_id,
                status="received"
            )

        if message.message_type in self.message_handlers:
            try:
                await self.message_handlers[message.message_type](message)

                # Send delivery confirmation to the message bus
                if message.message_type != MessageType.DELIVERY_CONFIRMATION:
                    await self.send_delivery_confirmation(
                        recipient="message_bus",
                        original_message_id=message.message_id,
                        status="delivered"
                    )
            except Exception as e:
                # Convert to appropriate error type if it's not already an AgenticKernelError
                if not isinstance(e, AgenticKernelError):
                    error = CommunicationError(
                        message=f"Error handling message of type {message.message_type.value}: {str(e)}",
                        details={
                            "message_id": message.message_id,
                            "message_type": message.message_type.value,
                            "sender": message.sender,
                            "recipient": message.recipient,
                            "original_error": str(e)
                        },
                        retry_possible=False
                    )
                else:
                    error = e

                self.error_handler.log_error(error, {
                    "message_id": message.message_id,
                    "message_type": message.message_type.value,
                    "sender": message.sender
                })

                # Send error message back to sender
                await self.send_error(
                    recipient=message.sender,
                    error_type=error.__class__.__name__,
                    description=str(error),
                    details=getattr(error, "details", {}),
                    recovery_hints=self.error_handler.generate_recovery_hints(error),
                    correlation_id=message.message_id
                )
        else:
            error = ProtocolError(
                message=f"No handler registered for message type {message.message_type.value}",
                code="UNHANDLED_MESSAGE_TYPE",
                details={
                    "message_id": message.message_id,
                    "message_type": message.message_type.value,
                    "sender": message.sender,
                    "recipient": self.agent_id
                },
                recovery_hints=[
                    f"Register a handler for message type {message.message_type.value}",
                    "Update the agent to support this message type",
                    "Check if the message type is correct"
                ],
                retry_possible=False
            )

            self.error_handler.log_error(error)

            # Send error message back to sender
            await self.send_error(
                recipient=message.sender,
                error_type="UNHANDLED_MESSAGE_TYPE",
                description=f"No handler registered for message type {message.message_type.value}",
                details={"message_type": message.message_type.value},
                recovery_hints=error.recovery_hints,
                correlation_id=message.message_id
            )

    async def _handle_message_ack(self, message: MessageAckMessage):
        """Handle an acknowledgment message.

        Args:
            message: The acknowledgment message
        """
        original_message_id = message.content.get("original_message_id")
        if not original_message_id:
            logger.warning(f"Received acknowledgment without original_message_id: {message.message_id}")
            return

        # Update the original message's acknowledgment status
        if original_message_id in self.sent_messages:
            original_message = self.sent_messages[original_message_id]
            original_message.acknowledgment_received = True
            logger.debug(f"Acknowledgment received for message {original_message_id}")

            # Remove from pending acknowledgments
            if original_message_id in self.pending_acknowledgments:
                del self.pending_acknowledgments[original_message_id]
        else:
            logger.warning(f"Received acknowledgment for unknown message: {original_message_id}")

    async def _handle_delivery_confirmation(self, message: DeliveryConfirmationMessage):
        """Handle a delivery confirmation message.

        Args:
            message: The delivery confirmation message
        """
        original_message_id = message.content.get("original_message_id")
        if not original_message_id:
            logger.warning(f"Received delivery confirmation without original_message_id: {message.message_id}")
            return

        # Update the original message's delivery status
        if original_message_id in self.sent_messages:
            original_message = self.sent_messages[original_message_id]
            original_message.delivery_confirmed = True
            logger.debug(f"Delivery confirmed for message {original_message_id}")

            # Remove from pending confirmations
            if original_message_id in self.pending_confirmations:
                del self.pending_confirmations[original_message_id]
        else:
            logger.warning(f"Received delivery confirmation for unknown message: {original_message_id}")

    async def _handle_message_retry(self, message: MessageRetryMessage):
        """Handle a message retry request.

        Args:
            message: The message retry request
        """
        original_message_id = message.content.get("original_message_id")
        if not original_message_id:
            logger.warning(f"Received retry request without original_message_id: {message.message_id}")
            return

        # Check if we have the original message
        if original_message_id in self.sent_messages:
            original_message = self.sent_messages[original_message_id]

            # Increment delivery attempts
            original_message.delivery_attempts += 1

            # Check if we've exceeded max delivery attempts
            max_attempts = original_message.max_delivery_attempts or 3
            if original_message.delivery_attempts > max_attempts:
                logger.warning(f"Max delivery attempts exceeded for message {original_message_id}")
                return

            # Retry sending the message
            logger.info(f"Retrying message {original_message_id}, attempt {original_message.delivery_attempts}")
            await self.message_bus.publish(original_message)
        else:
            logger.warning(f"Received retry request for unknown message: {original_message_id}")

    def _validate_message(self, message: Message) -> None:
        """Validate a message before sending.

        Args:
            message: The message to validate

        Raises:
            MessageValidationError: If validation fails
        """
        # Basic validation for all messages
        required_fields = ["message_id", "message_type", "sender", "recipient", "content"]
        message_dict = {
            "message_id": message.message_id,
            "message_type": message.message_type,
            "sender": message.sender,
            "recipient": message.recipient,
            "content": message.content,
            "priority": message.priority,
            "correlation_id": message.correlation_id,
            "timestamp": message.timestamp
        }

        self.error_handler.validate_message(
            message_dict, 
            required_fields,
            field_types={
                "message_id": str,
                "sender": str,
                "recipient": str,
                "content": dict
            }
        )

        # Additional validation based on message type
        if message.message_type == MessageType.TASK_REQUEST:
            self.error_handler.validate_message(
                message.content,
                ["task_description", "parameters"],
                field_types={
                    "task_description": str,
                    "parameters": dict
                }
            )
        elif message.message_type == MessageType.QUERY:
            self.error_handler.validate_message(
                message.content,
                ["query"],
                field_types={"query": str}
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
        details: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
        recovery_hints: Optional[List[str]] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """Send an error message to another agent.

        This method formats and sends a standardized error message to another agent.
        It can be used to report errors encountered during processing or to respond
        to invalid requests.

        Args:
            recipient: ID of the receiving agent
            error_type: Type of error (e.g., "MESSAGE_VALIDATION_ERROR")
            description: Human-readable error description
            details: Additional error details as a dictionary
            stack_trace: Optional stack trace for debugging
            recovery_hints: Suggestions for recovering from the error
            correlation_id: Optional ID of the message that caused the error

        Returns:
            The message ID of the sent error message

        Raises:
            MessageDeliveryError: If the error message cannot be delivered
        """
        # Create standardized error content
        content = {
            "error_type": error_type,
            "description": description,
            "details": details or {},
            "recovery_hints": recovery_hints or [],
            "timestamp": datetime.utcnow().isoformat(),
            "sender_id": self.agent_id,
        }

        # Add stack trace if provided and we're in debug mode
        if stack_trace and logger.isEnabledFor(logging.DEBUG):
            content["stack_trace"] = stack_trace

        # Log the error being sent
        self.error_handler.log_error(
            CommunicationError(
                message=f"Sending error to {recipient}: {error_type} - {description}",
                code=error_type,
                details=details,
                recovery_hints=recovery_hints,
                severity=ErrorSeverity.INFO  # This is just informational since we're sending, not receiving
            ),
            {"recipient": recipient, "correlation_id": correlation_id}
        )

        # Send the error message with high priority
        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.ERROR,
            content=content,
            priority=MessagePriority.HIGH,
            correlation_id=correlation_id,
            validate=True  # Ensure the error message itself is valid
        )

    # A2A-specific methods

    async def request_capabilities(
        self,
        recipient: str,
        capability_types: Optional[List[str]] = None,
        detail_level: str = "basic",
    ) -> str:
        """Request capabilities from another agent.

        Args:
            recipient: ID of the agent to query for capabilities
            capability_types: Optional list of capability types to filter by
            detail_level: Level of detail requested (basic, detailed, full)

        Returns:
            The message ID of the capability request
        """
        content = {
            "capability_types": capability_types,
            "detail_level": detail_level,
        }

        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.CAPABILITY_REQUEST,
            content=content,
        )

    async def send_capability_response(
        self,
        request_id: str,
        recipient: str,
        capabilities: List[Dict[str, Any]],
        performance_metrics: Optional[Dict[str, Any]] = None,
        limitations: Optional[Dict[str, Any]] = None,
    ):
        """Send a response to a capability request.

        Args:
            request_id: ID of the original capability request
            recipient: ID of the requesting agent
            capabilities: List of capability descriptions
            performance_metrics: Optional metrics for each capability
            limitations: Any limitations or constraints on capabilities
        """
        content = {
            "capabilities": capabilities,
            "performance_metrics": performance_metrics or {},
            "limitations": limitations or {},
        }

        await self.send_message(
            recipient=recipient,
            message_type=MessageType.CAPABILITY_RESPONSE,
            content=content,
            correlation_id=request_id,
        )

    async def announce_discovery(
        self,
        recipient: str,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        status: str = "active",
        resources: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Announce agent discovery and capabilities.

        Args:
            recipient: ID of the receiving agent (often a registry or all agents)
            agent_id: Unique identifier for the agent
            agent_type: Type/role of the agent
            capabilities: List of agent capabilities
            status: Current operational status
            resources: Available resources and constraints
            metadata: Additional agent-specific information

        Returns:
            The message ID of the discovery announcement
        """
        content = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities,
            "status": status,
            "resources": resources or {},
            "metadata": metadata or {},
        }

        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.AGENT_DISCOVERY,
            content=content,
            priority=MessagePriority.NORMAL,
        )

    async def request_consensus(
        self,
        recipients: List[str],
        topic: str,
        options: List[Any],
        context: Dict[str, Any],
        voting_deadline: Optional[datetime] = None,
        voting_mechanism: str = "majority",
        min_participants: int = 1,
    ) -> Dict[str, str]:
        """Request consensus on a decision from multiple agents.

        Args:
            recipients: IDs of the agents to participate in consensus
            topic: The topic requiring consensus
            options: Available options to choose from
            context: Context information for the decision
            voting_deadline: Optional deadline for voting
            voting_mechanism: How votes will be tallied (majority, weighted, unanimous)
            min_participants: Minimum number of participants required

        Returns:
            Dictionary mapping recipient IDs to message IDs
        """
        content = {
            "topic": topic,
            "options": options,
            "context": context,
            "voting_deadline": voting_deadline.isoformat() if voting_deadline else None,
            "voting_mechanism": voting_mechanism,
            "min_participants": min_participants,
        }

        # Generate a conversation ID for this consensus process
        conversation_id = str(uuid.uuid4())

        # Send to all recipients
        message_ids = {}
        for recipient in recipients:
            message_id = await self.send_message(
                recipient=recipient,
                message_type=MessageType.CONSENSUS_REQUEST,
                content=content,
                priority=MessagePriority.NORMAL,
                # Use the same conversation_id for all messages in this consensus
                # This will be passed in the metadata
            )
            message_ids[recipient] = message_id

        return message_ids

    async def send_consensus_vote(
        self,
        request_id: str,
        recipient: str,
        consensus_id: str,
        vote: Any,
        confidence: float = 1.0,
        rationale: Optional[str] = None,
    ):
        """Send a vote in a consensus process.

        Args:
            request_id: ID of the original consensus request
            recipient: ID of the agent that requested consensus
            consensus_id: ID of the consensus request
            vote: The agent's vote
            confidence: Confidence level in the vote (0.0-1.0)
            rationale: Explanation for the vote
        """
        content = {
            "consensus_id": consensus_id,
            "vote": vote,
            "confidence": confidence,
            "rationale": rationale,
        }

        await self.send_message(
            recipient=recipient,
            message_type=MessageType.CONSENSUS_VOTE,
            content=content,
            correlation_id=request_id,
        )

    async def send_consensus_result(
        self,
        recipients: List[str],
        consensus_id: str,
        result: Any,
        vote_distribution: Dict[str, Any],
        confidence: float = 1.0,
        next_steps: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Send the result of a consensus process to multiple agents.

        Args:
            recipients: IDs of the agents that participated in consensus
            consensus_id: ID of the consensus request
            result: The consensus result
            vote_distribution: Distribution of votes
            confidence: Overall confidence in the result
            next_steps: Any actions to be taken based on the result

        Returns:
            Dictionary mapping recipient IDs to message IDs
        """
        content = {
            "consensus_id": consensus_id,
            "result": result,
            "vote_distribution": vote_distribution,
            "confidence": confidence,
            "next_steps": next_steps or [],
        }

        # Send to all recipients
        message_ids = {}
        for recipient in recipients:
            message_id = await self.send_message(
                recipient=recipient,
                message_type=MessageType.CONSENSUS_RESULT,
                content=content,
                priority=MessagePriority.NORMAL,
            )
            message_ids[recipient] = message_id

        return message_ids

    async def notify_conflict(
        self,
        recipients: List[str],
        conflict_type: str,
        description: str,
        parties: List[str],
        impact: Dict[str, Any],
        resolution_deadline: Optional[datetime] = None,
    ) -> Dict[str, str]:
        """Notify agents about a conflict.

        Args:
            recipients: IDs of the agents to notify about the conflict
            conflict_type: Type of conflict
            description: Description of the conflict
            parties: Agents involved in the conflict
            impact: Impact assessment of the conflict
            resolution_deadline: Deadline for resolution

        Returns:
            Dictionary mapping recipient IDs to message IDs
        """
        content = {
            "conflict_type": conflict_type,
            "description": description,
            "parties": parties,
            "impact": impact,
            "resolution_deadline": (
                resolution_deadline.isoformat() if resolution_deadline else None
            ),
        }

        # Send to all recipients
        message_ids = {}
        for recipient in recipients:
            message_id = await self.send_message(
                recipient=recipient,
                message_type=MessageType.CONFLICT_NOTIFICATION,
                content=content,
                priority=MessagePriority.HIGH,
            )
            message_ids[recipient] = message_id

        return message_ids

    async def send_conflict_resolution(
        self,
        recipients: List[str],
        conflict_id: str,
        resolution: str,
        rationale: str,
        required_actions: Dict[str, List[str]],
        verification_method: str,
    ) -> Dict[str, str]:
        """Send a conflict resolution to multiple agents.

        Args:
            recipients: IDs of the agents to receive the resolution
            conflict_id: ID of the conflict being resolved
            resolution: The proposed resolution
            rationale: Explanation for the resolution
            required_actions: Actions required from involved parties
            verification_method: How to verify the conflict is resolved

        Returns:
            Dictionary mapping recipient IDs to message IDs
        """
        content = {
            "conflict_id": conflict_id,
            "resolution": resolution,
            "rationale": rationale,
            "required_actions": required_actions,
            "verification_method": verification_method,
        }

        # Send to all recipients
        message_ids = {}
        for recipient in recipients:
            message_id = await self.send_message(
                recipient=recipient,
                message_type=MessageType.CONFLICT_RESOLUTION,
                content=content,
                priority=MessagePriority.HIGH,
            )
            message_ids[recipient] = message_id

        return message_ids

    async def send_feedback(
        self,
        recipient: str,
        feedback_type: str,
        rating: Optional[float] = None,
        description: str = "",
        improvement_suggestions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send feedback to an agent.

        Args:
            recipient: ID of the agent to receive feedback
            feedback_type: Type of feedback (performance, behavior, outcome)
            rating: Numerical rating (if applicable)
            description: Detailed feedback description
            improvement_suggestions: Suggestions for improvement
            context: Context in which the feedback applies

        Returns:
            The message ID of the feedback message
        """
        content = {
            "feedback_type": feedback_type,
            "rating": rating,
            "description": description,
            "improvement_suggestions": improvement_suggestions or [],
            "context": context or {},
        }

        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.FEEDBACK,
            content=content,
            priority=MessagePriority.NORMAL,
        )

    async def request_coordination(
        self,
        recipient: str,
        coordination_type: str,
        activities: List[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]] = None,
        dependencies: Optional[Dict[str, List[str]]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> str:
        """Request coordination with another agent.

        Args:
            recipient: ID of the agent to coordinate with
            coordination_type: Type of coordination needed
            activities: Activities requiring coordination
            constraints: Timing or resource constraints
            dependencies: Dependencies on other agents or activities
            priority: Priority of the coordination request

        Returns:
            The message ID of the coordination request
        """
        content = {
            "coordination_type": coordination_type,
            "activities": activities,
            "constraints": constraints or {},
            "dependencies": dependencies or {},
        }

        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.COORDINATION_REQUEST,
            content=content,
            priority=priority,
        )

    async def send_coordination_response(
        self,
        request_id: str,
        recipient: str,
        coordination_id: str,
        response: str,
        availability: Dict[str, Any],
        conditions: Optional[Dict[str, Any]] = None,
        proposed_schedule: Optional[Dict[str, Any]] = None,
    ):
        """Send a response to a coordination request.

        Args:
            request_id: ID of the original coordination request
            recipient: ID of the agent that requested coordination
            coordination_id: ID of the coordination request
            response: Accept, reject, or propose alternative
            availability: Agent's availability for coordination
            conditions: Any conditions for coordination
            proposed_schedule: Proposed timing for coordinated activities
        """
        content = {
            "coordination_id": coordination_id,
            "response": response,
            "availability": availability,
            "conditions": conditions or {},
            "proposed_schedule": proposed_schedule or {},
        }

        await self.send_message(
            recipient=recipient,
            message_type=MessageType.COORDINATION_RESPONSE,
            content=content,
            correlation_id=request_id,
        )

    async def send_task_decomposition(
        self,
        recipient: str,
        parent_task_id: str,
        subtasks: List[Dict[str, Any]],
        dependencies: Optional[Dict[str, List[str]]] = None,
        allocation_suggestions: Optional[Dict[str, List[str]]] = None,
        estimated_complexity: Optional[Dict[str, float]] = None,
    ) -> str:
        """Send a task decomposition to another agent.

        Args:
            recipient: ID of the agent to receive the decomposition
            parent_task_id: ID of the parent task
            subtasks: List of subtask descriptions
            dependencies: Dependencies between subtasks
            allocation_suggestions: Suggestions for which agents should handle which subtasks
            estimated_complexity: Complexity assessment for each subtask

        Returns:
            The message ID of the task decomposition message
        """
        content = {
            "parent_task_id": parent_task_id,
            "subtasks": subtasks,
            "dependencies": dependencies or {},
            "allocation_suggestions": allocation_suggestions or {},
            "estimated_complexity": estimated_complexity or {},
        }

        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.TASK_DECOMPOSITION,
            content=content,
            priority=MessagePriority.NORMAL,
        )
