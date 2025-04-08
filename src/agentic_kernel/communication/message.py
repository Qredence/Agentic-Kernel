"""Message types and protocols for agent communication.

This module defines the core message types and protocols used for communication
between agents in the Agentic-Kernel system.

Key features:
1. Standardized message format
2. Type-safe message construction
3. Protocol definitions
4. Message validation
5. Serialization support
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class MessageType(Enum):
    """Types of messages that can be exchanged between agents."""

    TASK_REQUEST = "task_request"  # Request another agent to perform a task
    TASK_RESPONSE = "task_response"  # Response to a task request
    QUERY = "query"  # Query for information
    QUERY_RESPONSE = "query_response"  # Response to a query
    STATUS_UPDATE = "status_update"  # Agent status update
    ERROR = "error"  # Error notification
    CAPABILITY_REQUEST = "capability_request"  # Request for agent capabilities
    CAPABILITY_RESPONSE = "capability_response"  # Response with agent capabilities
    AGENT_DISCOVERY = "agent_discovery"  # Agent discovery and registration message


class MessagePriority(Enum):
    """Priority levels for messages."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Message(BaseModel):
    """Base message type for agent communication.

    This class defines the standard structure for all messages exchanged
    between agents in the system.

    Attributes:
        message_id: Unique identifier for the message
        message_type: Type of message
        sender: ID of the sending agent
        recipient: ID of the receiving agent
        content: Message payload
        priority: Message priority level
        timestamp: When the message was created
        correlation_id: ID to link related messages
        metadata: Additional message metadata
    """

    message_id: str = Field(..., description="Unique identifier for the message")
    message_type: MessageType = Field(..., description="Type of message")
    sender: str = Field(..., description="ID of the sending agent")
    recipient: str = Field(..., description="ID of the receiving agent")
    content: Dict[str, Any] = Field(..., description="Message payload")
    priority: MessagePriority = Field(default=MessagePriority.NORMAL)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = Field(
        None, description="ID to link related messages"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskRequest(Message):
    """Message for requesting task execution from another agent.

    This message type is used when one agent needs another agent to perform
    a specific task.

    The content field should contain:
    - task_description: Description of the task to perform
    - parameters: Task parameters
    - constraints: Any constraints on execution
    - deadline: Optional deadline for completion
    """

    message_type: MessageType = MessageType.TASK_REQUEST


class TaskResponse(Message):
    """Message for responding to a task request.

    This message type is used to return the results of a requested task
    execution.

    The content field should contain:
    - status: Task execution status
    - result: Task execution result
    - error: Error information if task failed
    - metrics: Performance metrics
    """

    message_type: MessageType = MessageType.TASK_RESPONSE


class Query(Message):
    """Message for querying information from another agent.

    This message type is used when one agent needs to request information
    from another agent.

    The content field should contain:
    - query: The query string or structured query
    - context: Any relevant context for the query
    - required_format: Optional format for the response
    """

    message_type: MessageType = MessageType.QUERY


class QueryResponse(Message):
    """Message for responding to an information query.

    This message type is used to return the requested information to
    a querying agent.

    The content field should contain:
    - result: The query result
    - confidence: Confidence level in the result
    - source: Source of the information
    """

    message_type: MessageType = MessageType.QUERY_RESPONSE


class StatusUpdate(Message):
    """Message for providing status updates.

    This message type is used to inform other agents about changes in
    an agent's status or state.

    The content field should contain:
    - status: Current status
    - details: Status details
    - resources: Available resources
    """

    message_type: MessageType = MessageType.STATUS_UPDATE


class ErrorMessage(Message):
    """Message for communicating errors.

    This message type is used to inform other agents about errors
    that have occurred.

    The content field should contain:
    - error_type: Type of error
    - description: Error description
    - stack_trace: Optional stack trace
    - recovery_hints: Optional recovery suggestions
    """

    message_type: MessageType = MessageType.ERROR


class AgentDiscoveryMessage(Message):
    """Message for agent discovery and registration.

    This message type is used when agents announce their presence,
    capabilities, and availability to the system.

    The content field should contain:
    - agent_id: Unique identifier for the agent
    - agent_type: Type/role of the agent
    - capabilities: List of agent capabilities
    - status: Current operational status
    - resources: Available resources and constraints
    - metadata: Additional agent-specific information
    """

    message_type: MessageType = MessageType.AGENT_DISCOVERY
