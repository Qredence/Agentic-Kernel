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
from datetime import datetime
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
    ErrorMessage,
    FeedbackMessage,
    Message,
    MessagePriority,
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

        # Register with message bus
        self.message_bus.subscribe(agent_id, self._handle_message)

    async def send_message(
        self,
        recipient: str,
        message_type: MessageType,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        validate: bool = True,
    ) -> str:
        """Send a message to another agent.

        Args:
            recipient: ID of the receiving agent
            message_type: Type of message to send
            content: Message content
            priority: Message priority
            correlation_id: Optional ID to link related messages
            validate: Whether to validate the message before sending

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
            try:
                await self.message_handlers[message.message_type](message)
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
